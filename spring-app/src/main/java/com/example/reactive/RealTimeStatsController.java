package com.example.reactive;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;

@RestController
public class RealTimeStatsController {
    
    @GetMapping("/real-time-stats")
    public Map<String, Object> getRealTimeStats() {
        return Map.of(
            "timestamp", java.time.Instant.now(),
            "totalEnqueued", QueueController.getTotalEnqueued(),
            "totalDequeued", QueueController.getTotalDequeued(),
            "gap", QueueController.getTotalEnqueued() - QueueController.getTotalDequeued(),
            "lastActivity", QueueController.getLastActivity()
        );
    }
}