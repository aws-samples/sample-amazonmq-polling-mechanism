package com.example.reactive;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import jakarta.jms.ConnectionFactory;
import jakarta.jms.Connection;
import jakarta.jms.Session;
import jakarta.jms.Queue;
import jakarta.jms.MessageConsumer;
import jakarta.jms.Message;
import jakarta.jms.TextMessage;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

@RestController
public class RetryController {
    
    private static final Logger log = LoggerFactory.getLogger(RetryController.class);
    
    @Autowired(required = false)
    private ConnectionFactory connectionFactory;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @PostMapping("/retry-gap-messages")
    public Map<String, Object> retryGapMessages() {
        Map<String, Object> result = new HashMap<>();
        List<String> processedItems = new ArrayList<>();
        int retryCount = 0;
        
        if (connectionFactory == null) {
            result.put("error", "JMS not configured");
            return result;
        }
        
        try (Connection connection = connectionFactory.createConnection()) {
            connection.start();
            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            Queue queue = session.createQueue("item.queue");
            MessageConsumer consumer = session.createConsumer(queue);
            
            // Try to consume stuck messages with timeout
            Message message;
            while ((message = consumer.receive(2000)) != null && retryCount < 10) {
                retryCount++;
                
                try {
                    if (message instanceof TextMessage) {
                        String messageContent = ((TextMessage) message).getText();
                        log.info("🔄 MANUAL RETRY: Processing stuck message {}", message.getJMSMessageID());
                        
                        // Parse and process manually
                        Item item = objectMapper.readValue(messageContent, Item.class);
                        
                        // Update counters manually
                        synchronized(QueueController.class) {
                            QueueController.addQueueActivity(java.time.Instant.now() + ": MANUAL RETRY item " + item.getId());
                        }
                        
                        processedItems.add(item.getId());
                        log.info("✅ MANUAL SUCCESS: {}", item.getId());
                    }
                } catch (Exception e) {
                    log.error("❌ Manual retry failed: {}", e.getMessage());
                }
            }
            
            result.put("status", "SUCCESS");
            result.put("retriedCount", retryCount);
            result.put("processedItems", processedItems);
            result.put("message", "Manually processed " + retryCount + " stuck messages");
            
        } catch (Exception e) {
            result.put("status", "FAILED");
            result.put("error", e.getMessage());
        }
        
        return result;
    }
}