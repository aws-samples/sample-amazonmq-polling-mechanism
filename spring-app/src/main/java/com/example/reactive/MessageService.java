package com.example.reactive;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jms.annotation.JmsListener;
import org.springframework.jms.core.JmsTemplate;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.retry.annotation.Retryable;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Backoff;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.handler.annotation.Header;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.concurrent.CompletableFuture;

@Service
public class MessageService {

    private static final Logger log = LoggerFactory.getLogger(MessageService.class);
    private final JmsTemplate jmsTemplate;
    private final DynamoService dynamoService;
    private final ObjectMapper objectMapper;
    
    @Value("${jms.queue.name:item.queue}")
    private String queueName;

    public MessageService(@Autowired(required = false) JmsTemplate jmsTemplate, DynamoService dynamoService, ObjectMapper objectMapper) {
        this.jmsTemplate = jmsTemplate;
        this.dynamoService = dynamoService;
        this.objectMapper = objectMapper;
    }

    public void sendMessage(Item item) {
        try {
            log.info("=== QUEUE START === {}", java.time.Instant.now());
            log.info("Sending message for item: {}, delay: {}s", item.getId(), item.getDelay());
            
            if (item.getDelay() > 0 && !"High".equals(item.getPriority())) {
                // Set status to processing for delayed items (except High priority)
                dynamoService.updateItemStatus(item.getId(), "processing");
                log.info("Item {} set to processing status, will queue to MQ after {}s delay", item.getId(), item.getDelay());
                
                // Schedule delayed MQ sending
                CompletableFuture.runAsync(() -> {
                    try {
                        log.info("Waiting {}s before sending to MQ for item: {}", item.getDelay(), item.getId());
                        Thread.sleep(item.getDelay() * 1000L);
                        
                        // Send to MQ after delay with properties
                        String message = objectMapper.writeValueAsString(item);
                        log.info("=== SENDING TO MQ AFTER DELAY === item: {} at {}", item.getId(), java.time.Instant.now());
                        
                        if (jmsTemplate != null) {
                            long seqNum = QueueController.getNextSequence();
                            jmsTemplate.send(queueName, session -> {
                                jakarta.jms.TextMessage textMessage = session.createTextMessage(message);
                                textMessage.setStringProperty("itemId", item.getId());
                                textMessage.setLongProperty("timestamp", System.currentTimeMillis());
                                textMessage.setIntProperty("delay", item.getDelay());
                                textMessage.setLongProperty("sequenceNumber", seqNum);
                                textMessage.setJMSPriority(getPriorityLevel(item.getPriority()));
                                textMessage.setJMSDeliveryMode(jakarta.jms.DeliveryMode.PERSISTENT);
                                return textMessage;
                            });
                            log.info("📤 Message sent with sequence: {} for item: {}", seqNum, item.getId());
                        } else {
                            log.warn("JmsTemplate not available - message not sent");
                        }
                        
                        log.info("✅ Message QUEUED to MQ after {}s delay for item: {} at {}", item.getDelay(), item.getId(), java.time.Instant.now());
                        
                        // Track queue activity
                        QueueController.addQueueActivity(java.time.Instant.now() + ": QUEUED item " + item.getId());
                        
                    } catch (Exception e) {
                        log.error("Failed to send delayed message to MQ: {}", e.getMessage(), e);
                    }
                });
            } else {
                // Send immediate message to MQ (delay = 0 OR High priority)
                try {
                    String message = objectMapper.writeValueAsString(item);
                    if ("High".equals(item.getPriority()) && item.getDelay() > 0) {
                        log.info("=== HIGH PRIORITY - BYPASSING {}s DELAY ===", item.getDelay());
                    } else {
                        log.info("=== SENDING IMMEDIATE TO MQ ===");
                    }
                    
                    if (jmsTemplate != null) {
                        jmsTemplate.send(queueName, session -> {
                            jakarta.jms.TextMessage textMessage = session.createTextMessage(message);
                            textMessage.setStringProperty("itemId", item.getId());
                            textMessage.setLongProperty("timestamp", System.currentTimeMillis());
                            textMessage.setIntProperty("delay", 0);
                            textMessage.setLongProperty("sequenceNumber", QueueController.getNextSequence());
                            textMessage.setJMSPriority(getPriorityLevel(item.getPriority()));
                            return textMessage;
                        });
                        log.info("Immediate message sent to MQ");
                    } else {
                        log.warn("JmsTemplate not available - immediate message not sent");
                    }
                    
                    // Track immediate queue activity
                    QueueController.addQueueActivity(java.time.Instant.now() + ": QUEUED immediate item " + item.getId());
                } catch (Exception e) {
                    log.error("Failed to send immediate message to MQ: {}", e.getMessage(), e);
                }
            }
            log.info("=== QUEUE COMPLETE === {}", java.time.Instant.now());
        } catch (Exception e) {
            log.error("Failed to send message: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to send message", e);
        }
    }
    
    @JmsListener(destination = "item.queue")
    @Retryable(
        value = {Exception.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 1000, multiplier = 2, random = true)
    )
    public void processMessage(
        String messageBody,
        jakarta.jms.Message jmsMessage
    ) {
        String itemId = null;
        try {
            log.info("🎯 PROCESSING MESSAGE: {}", messageBody);
            
            Item item = objectMapper.readValue(messageBody, Item.class);
            itemId = item.getId();
            
            int messagePriority = jmsMessage.getJMSPriority();
            String priorityLevel = getPriorityName(messagePriority);
            log.info("📨 Processing {} priority item: {} at {}", priorityLevel, itemId, java.time.Instant.now());
            
            // Check if item exists in DynamoDB, create if missing
            try {
                dynamoService.getItem(item.getId());
                log.info("✅ Item exists in DynamoDB: {}", itemId);
            } catch (Exception e) {
                log.warn("⚠️ Item not found in DynamoDB, creating: {}", itemId);
                dynamoService.createItem(item);
                log.info("✅ Item created in DynamoDB: {}", itemId);
            }
            
            // Update DynamoDB status to completed
            dynamoService.updateItemStatus(item.getId(), "completed");
            dynamoService.updateItemModified(item.getId());
            
            // Manual acknowledgment (CLIENT_ACKNOWLEDGE)
            jmsMessage.acknowledge();
            log.info("✅ Message acknowledged successfully");
            
            // Update counters
            QueueController.incrementDequeued();
            
            // Track activity
            QueueController.addQueueActivity(
                java.time.Instant.now() + ": PROCESSED item " + itemId
            );
            
            log.info("✅ Successfully processed {} priority item: {}", priorityLevel, itemId);
            
        } catch (Exception e) {
            log.error("❌ Failed to process message for item: {} - WILL RETRY", itemId, e);
            
            // Do NOT acknowledge failed message (CLIENT_ACKNOWLEDGE)
            log.warn("⚠️ Message NOT acknowledged - will be redelivered");
            
            // Update status to processing-retry for tracking
            if (itemId != null) {
                try {
                    dynamoService.updateItemStatus(itemId, "processing-retry");
                } catch (Exception dbError) {
                    log.error("Failed to update retry status: {}", dbError.getMessage());
                }
            }
            
            throw new RuntimeException("Processing failed for item: " + itemId, e);
        }
    }
    
    @Recover
    public void recoverFromFailure(
        RuntimeException ex, 
        String messageBody,
        jakarta.jms.Message jmsMessage
    ) {
        String itemId = "unknown";
        try {
            Item item = objectMapper.readValue(messageBody, Item.class);
            itemId = item.getId();
            
            log.error("🚨 FINAL FAILURE - Max Spring retries exceeded for item: {}", itemId, ex);
            
            // Update status to permanent failure
            dynamoService.updateItemStatus(itemId, "permanent-failure");
            
            // Acknowledge the message to send to DLQ
            jmsMessage.acknowledge();
            log.warn("⚠️ Failed message acknowledged - will be sent to DLQ by ActiveMQ");
            
            QueueController.addQueueActivity(
                java.time.Instant.now() + ": PERMANENT FAILURE item " + itemId
            );
            
            log.error("💀 Item {} will be sent to DLQ after acknowledgment", itemId);
            
        } catch (Exception e) {
            log.error("Failed to handle recovery for item {}: {}", itemId, e.getMessage(), e);
            
            // Even if recovery fails, acknowledge to prevent infinite loop
            try {
                jmsMessage.acknowledge();
                log.warn("⚠️ Recovery failed but message acknowledged to prevent loop");
            } catch (Exception ackError) {
                log.error("Failed to acknowledge message during recovery failure: {}", ackError.getMessage());
            }
        }
    }
    
    private int getPriorityLevel(String priority) {
        if (priority == null) return 4; // Default medium
        switch (priority.toUpperCase()) {
            case "HIGH": return 9; // High priority (0-9, 9 is highest)
            case "MEDIUM": return 4; // Medium priority
            case "LOW": return 0; // Low priority
            default: return 4;
        }
    }
    
    private String getPriorityName(int priority) {
        if (priority >= 7) return "HIGH";
        if (priority >= 3) return "MEDIUM";
        return "LOW";
    }
}