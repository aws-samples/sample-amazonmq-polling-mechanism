package com.example.reactive;

import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jms.annotation.JmsListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.jms.ConnectionFactory;
import jakarta.jms.Connection;
import jakarta.jms.Session;
import jakarta.jms.Queue;
import jakarta.jms.QueueBrowser;
import jakarta.jms.Message;
import java.util.*;

@RestController
@RequestMapping("/api/queue")
@CrossOrigin(origins = "*")
public class QueueController {

    private static final Logger log = LoggerFactory.getLogger(QueueController.class);
    
    @Autowired(required = false)
    private ConnectionFactory connectionFactory;
    
    @Autowired
    private DynamoService dynamoService;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Autowired
    private MQStatsService mqStatsService;
    
    private static final java.util.List<String> queueActivity = new java.util.concurrent.CopyOnWriteArrayList<>();
    private static long totalEnqueued = 0;
    private static long totalDequeued = 0;
    private static long totalDlqCount = 0;
    private static final java.util.Set<String> processedMessageIds = java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static final java.util.concurrent.atomic.AtomicLong expectedSequenceNumber = new java.util.concurrent.atomic.AtomicLong(1);
    private static final java.util.List<String> skippedMessages = new java.util.concurrent.CopyOnWriteArrayList<>();
    private static final java.util.concurrent.atomic.AtomicLong messageSequence = new java.util.concurrent.atomic.AtomicLong(0);
    
    public static synchronized void addQueueActivity(String activity) {
        queueActivity.add(0, activity);
        if (queueActivity.size() > 50) queueActivity.remove(queueActivity.size() - 1);
        
        // Track totals with immediate logging
        if (activity.contains("QUEUED")) {
            totalEnqueued++;
            log.info("📤 REAL-TIME: QUEUED counter = {}", totalEnqueued);
        } else if (activity.contains("DEQUEUED")) {
            totalDequeued++;
            log.info("📥 REAL-TIME: DEQUEUED counter = {} (gap: {})", totalDequeued, totalEnqueued - totalDequeued);
        }
    }
    
    public static void resetCounters() {
        queueActivity.clear();
        totalEnqueued = 0;
        totalDequeued = 0;
        totalDlqCount = 0;
        log.info("All queue counters and activity reset");
    }
    
    public static long getNextSequence() {
        return messageSequence.incrementAndGet();
    }
    
    public static long getTotalEnqueued() {
        return totalEnqueued;
    }
    
    public static long getTotalDequeued() {
        return totalDequeued;
    }
    
    public static String getLastActivity() {
        return queueActivity.isEmpty() ? "None" : queueActivity.get(0);
    }

    @GetMapping("/status")
    public Map<String, Object> getQueueStatus() {
        Map<String, Object> status = new HashMap<>();
        if (connectionFactory == null) {
            status.put("status", "disabled");
            status.put("error", "JMS not configured");
            return status;
        }
        
        try (Connection connection = connectionFactory.createConnection()) {
            connection.start();
            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            Queue queue = session.createQueue("item.queue");
            
            // Try to get queue browser (may not work with Amazon MQ)
            try {
                QueueBrowser browser = session.createBrowser(queue);
                Enumeration<?> enumeration = browser.getEnumeration();
                
                int messageCount = 0;
                List<Map<String, Object>> messages = new ArrayList<>();
                
                while (enumeration.hasMoreElements()) {
                    messageCount++;
                    Message message = (Message) enumeration.nextElement();
                    Map<String, Object> msgInfo = new HashMap<>();
                    msgInfo.put("messageId", message.getJMSMessageID());
                    msgInfo.put("timestamp", message.getJMSTimestamp());
                    messages.add(msgInfo);
                }
                
                status.put("queueName", "item.queue");
                status.put("messageCount", messageCount);
                status.put("messages", messages);
                status.put("status", "connected");
                status.put("note", "Queue browsing successful");
                status.put("recentActivity", queueActivity.size() > 10 ? queueActivity.subList(0, 10) : queueActivity);
                
                // Add application-level statistics (no JMX blocking)
                // Get current DLQ count
                try {
                    Queue dlq = session.createQueue("ActiveMQ.DLQ");
                    QueueBrowser dlqBrowser = session.createBrowser(dlq);
                    totalDlqCount = java.util.Collections.list(dlqBrowser.getEnumeration()).size();
                } catch (Exception dlqError) {
                    log.debug("Could not get DLQ count: {}", dlqError.getMessage());
                }
                
                status.put("statistics", Map.of(
                    "totalEnqueued", totalEnqueued,
                    "totalDequeued", totalDequeued,
                    "totalDlqCount", totalDlqCount,
                    "currentQueueSize", messageCount,
                    "consumerCount", 1,
                    "producerCount", 1,
                    "jmxEnabled", true
                ));
                
            } catch (Exception browserError) {
                log.warn("Queue browsing not supported: {}", browserError.getMessage());
                status.put("queueName", "item.queue");
                status.put("messageCount", "unknown");
                status.put("status", "connected");
                status.put("note", "Connected but browsing not supported by Amazon MQ");
            }
            
        } catch (Exception e) {
            log.error("Failed to connect to queue: {}", e.getMessage(), e);
            status.put("status", "error");
            status.put("error", e.getMessage());
        }
        return status;
    }
    
    @GetMapping("/detailed-stats")
    public Map<String, Object> getDetailedQueueStats() {
        Map<String, Object> detailedStats = new HashMap<>();
        
        try {
            // Get comprehensive JMX statistics
            Map<String, Object> jmxStats = mqStatsService.getQueueStatistics("item.queue");
            
            detailedStats.put("queueName", "item.queue");
            detailedStats.put("timestamp", java.time.Instant.now());
            detailedStats.put("jmxStats", jmxStats);
            
            // Application-level tracking
            detailedStats.put("applicationStats", Map.of(
                "totalEnqueued", totalEnqueued,
                "totalDequeued", totalDequeued,
                "recentActivityCount", queueActivity.size(),
                "lastActivity", queueActivity.isEmpty() ? "None" : queueActivity.get(0)
            ));
            
            // Performance metrics
            if (totalEnqueued > 0) {
                double processingRate = (double) totalDequeued / totalEnqueued * 100;
                detailedStats.put("performanceMetrics", Map.of(
                    "processingRate", String.format("%.1f%%", processingRate),
                    "pendingMessages", Math.max(0, totalEnqueued - totalDequeued)
                ));
            }
            
        } catch (Exception e) {
            log.error("Failed to get detailed stats: {}", e.getMessage(), e);
            detailedStats.put("error", e.getMessage());
        }
        
        return detailedStats;
    }
    
    @GetMapping("/message-gaps")
    public Map<String, Object> getMessageGaps() {
        Map<String, Object> result = new HashMap<>();
        result.put("skippedMessages", skippedMessages);
        result.put("processedMessageCount", processedMessageIds.size());
        result.put("expectedNextSequence", expectedSequenceNumber.get());
        result.put("totalEnqueued", totalEnqueued);
        result.put("totalDequeued", totalDequeued);
        result.put("gap", totalEnqueued - totalDequeued);
        return result;
    }
    
    @GetMapping("/dlq-check")
    public Map<String, Object> checkDeadLetterQueue() {
        Map<String, Object> result = new HashMap<>();
        
        if (connectionFactory == null) {
            result.put("error", "JMS not configured");
            return result;
        }
        
        try (Connection connection = connectionFactory.createConnection()) {
            connection.start();
            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            
            // Check main queue
            Queue mainQueue = session.createQueue("item.queue");
            QueueBrowser mainBrowser = session.createBrowser(mainQueue);
            List<Message> mainMessages = java.util.Collections.list(mainBrowser.getEnumeration());
            
            // Check DLQ
            Queue dlq = session.createQueue("ActiveMQ.DLQ");
            QueueBrowser dlqBrowser = session.createBrowser(dlq);
            List<Message> dlqMessages = java.util.Collections.list(dlqBrowser.getEnumeration());
            
            result.put("mainQueueCount", mainMessages.size());
            result.put("dlqCount", dlqMessages.size());
            
            // Extract DLQ message details with failure reasons
            List<Map<String, Object>> dlqDetails = new ArrayList<>();
            for (Message msg : dlqMessages) {
                Map<String, Object> msgInfo = new HashMap<>();
                msgInfo.put("messageId", msg.getJMSMessageID());
                msgInfo.put("timestamp", new java.util.Date(msg.getJMSTimestamp()));
                
                // Safe property extraction with null checks
                try {
                    // Sequence number (may not exist in older messages)
                    try {
                        long seqNum = msg.getLongProperty("sequenceNumber");
                        msgInfo.put("sequenceNumber", seqNum);
                    } catch (Exception e) {
                        msgInfo.put("sequenceNumber", "N/A");
                    }
                    
                    // Redelivery count and detailed failure analysis
                    try {
                        int deliveryCount = msg.getIntProperty("JMSXDeliveryCount");
                        msgInfo.put("redeliveryCount", deliveryCount);
                        
                        // Get message content for analysis
                        String messageContent = "";
                        if (msg instanceof jakarta.jms.TextMessage) {
                            try {
                                messageContent = ((jakarta.jms.TextMessage) msg).getText();
                            } catch (Exception e) {
                                messageContent = "[Content unavailable]";
                            }
                        }
                        
                        // Detailed failure reason analysis
                        StringBuilder dlqReason = new StringBuilder();
                        
                        if (deliveryCount == 1) {
                            dlqReason.append("FIRST ATTEMPT FAILURE: JMS Listener threw exception on initial processing. ");
                            dlqReason.append("Likely causes: (1) JMS Listener not configured/running, ");
                            dlqReason.append("(2) DynamoDB access denied, (3) JSON parsing error, ");
                            dlqReason.append("(4) Missing @JmsListener annotation or wrong destination");
                        } else if (deliveryCount >= 6) {
                            dlqReason.append("MAX REDELIVERY EXCEEDED: Message failed ").append(deliveryCount).append(" times. ");
                            dlqReason.append("Persistent issue: JMS Listener consistently throwing exceptions. ");
                            dlqReason.append("Check: Application logs, DynamoDB permissions, message format");
                        } else {
                            dlqReason.append("REPEATED FAILURE: Message failed ").append(deliveryCount).append(" times. ");
                            dlqReason.append("Intermittent issue: JMS Listener processing errors. ");
                            dlqReason.append("Check: Network connectivity, temporary service issues");
                        }
                        
                        // Add message analysis
                        if (messageContent.contains("\"id\":")) {
                            dlqReason.append(" | Message format: Valid JSON detected");
                        } else {
                            dlqReason.append(" | Message format: Invalid or corrupted JSON");
                        }
                        
                        // Add timestamp analysis
                        long messageAge = System.currentTimeMillis() - msg.getJMSTimestamp();
                        long ageMinutes = messageAge / (1000 * 60);
                        dlqReason.append(" | Message age: ").append(ageMinutes).append(" minutes");
                        
                        msgInfo.put("failureReason", dlqReason.toString());
                        msgInfo.put("messagePreview", messageContent.length() > 100 ? 
                            messageContent.substring(0, 100) + "..." : messageContent);
                        
                    } catch (Exception e) {
                        msgInfo.put("redeliveryCount", "Unknown");
                        msgInfo.put("failureReason", "ANALYSIS FAILED: Cannot determine failure cause - " + e.getMessage());
                    }
                    
                    // Original destination
                    try {
                        String origDest = msg.getStringProperty("_AMQ_ORIG_DESTINATION");
                        msgInfo.put("originalDestination", origDest != null ? origDest : "item.queue");
                    } catch (Exception e) {
                        msgInfo.put("originalDestination", "item.queue");
                    }
                    
                } catch (Exception e) {
                    msgInfo.put("failureReason", "DLQ message analysis failed");
                    msgInfo.put("sequenceNumber", "N/A");
                    msgInfo.put("redeliveryCount", "Unknown");
                }
                dlqDetails.add(msgInfo);
            }
            result.put("dlqMessages", dlqDetails);
            
        } catch (Exception e) {
            result.put("error", e.getMessage());
        }
        
        return result;
    }
    
    @PostMapping("/reset-tracking")
    public Map<String, Object> resetMessageTracking() {
        processedMessageIds.clear();
        skippedMessages.clear();
        expectedSequenceNumber.set(1);
        messageSequence.set(0);
        resetCounters();
        
        return Map.of(
            "status", "SUCCESS",
            "message", "All message tracking data reset"
        );
    }
    
    @PostMapping("/reprocess-dlq")
    public Map<String, Object> reprocessDlqMessages() {
        Map<String, Object> result = new HashMap<>();
        List<String> reprocessedItems = new ArrayList<>();
        int successCount = 0;
        int failCount = 0;
        
        if (connectionFactory == null) {
            result.put("error", "JMS not configured");
            return result;
        }
        
        try (Connection connection = connectionFactory.createConnection()) {
            connection.start();
            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            
            Queue dlq = session.createQueue("ActiveMQ.DLQ");
            QueueBrowser browser = session.createBrowser(dlq);
            Enumeration<?> enumeration = browser.getEnumeration();
            
            while (enumeration.hasMoreElements()) {
                try {
                    Message dlqMessage = (Message) enumeration.nextElement();
                    
                    if (dlqMessage instanceof jakarta.jms.TextMessage) {
                        String messageContent = ((jakarta.jms.TextMessage) dlqMessage).getText();
                        log.info("🔄 Reprocessing DLQ message: {}", dlqMessage.getJMSMessageID());
                        
                        Item item = objectMapper.readValue(messageContent, Item.class);
                        dynamoService.updateItemStatus(item.getId(), "recovered-from-dlq");
                        dynamoService.updateItemModified(item.getId());
                        
                        reprocessedItems.add(item.getId());
                        successCount++;
                        
                        log.info("✅ Successfully reprocessed DLQ item: {}", item.getId());
                    }
                } catch (Exception e) {
                    failCount++;
                    log.error("❌ Failed to reprocess DLQ message: {}", e.getMessage());
                }
            }
            
            result.put("status", "SUCCESS");
            result.put("reprocessedItems", reprocessedItems);
            result.put("successCount", successCount);
            result.put("failCount", failCount);
            result.put("message", "DLQ messages reprocessed manually");
            
        } catch (Exception e) {
            result.put("status", "FAILED");
            result.put("error", e.getMessage());
        }
        
        return result;
    }
    
    @PostMapping("/clear-dlq")
    public Map<String, Object> clearDlq() {
        Map<String, Object> result = new HashMap<>();
        
        if (connectionFactory == null) {
            result.put("error", "JMS not configured");
            return result;
        }
        
        try (Connection connection = connectionFactory.createConnection()) {
            connection.start();
            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            
            Queue dlq = session.createQueue("ActiveMQ.DLQ");
            jakarta.jms.MessageConsumer consumer = session.createConsumer(dlq);
            
            int clearedCount = 0;
            Message message;
            while ((message = consumer.receive(1000)) != null) {
                clearedCount++;
                log.info("🗑️ Cleared DLQ message: {}", message.getJMSMessageID());
            }
            
            result.put("status", "SUCCESS");
            result.put("clearedCount", clearedCount);
            result.put("message", "DLQ cleared");
            
        } catch (Exception e) {
            result.put("status", "FAILED");
            result.put("error", e.getMessage());
        }
        
        return result;
    }
    
    public static synchronized void incrementDequeued() {
        totalDequeued++;
        log.info("📥 DEQUEUED counter updated: {}", totalDequeued);
    }
}