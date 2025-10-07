package com.example.reactive;

import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Map;

@RestController
@RequestMapping("/api/queue")
@CrossOrigin(origins = "*")
public class QueuePurgeController {

    private static final Logger log = LoggerFactory.getLogger(QueuePurgeController.class);

    @PostMapping("/purge")
    public Map<String, Object> purgeQueue() {
        try {
            // Reset application-level counters
            QueueController.resetCounters();
            
            log.info("Queue purged - all counters reset");
            
            return Map.of(
                "status", "success",
                "message", "Queue purged and counters reset",
                "timestamp", java.time.Instant.now()
            );
            
        } catch (Exception e) {
            log.error("Failed to purge queue: {}", e.getMessage(), e);
            return Map.of(
                "status", "error",
                "message", e.getMessage()
            );
        }
    }
}