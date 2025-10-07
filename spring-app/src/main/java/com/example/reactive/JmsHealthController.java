package com.example.reactive;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import jakarta.jms.ConnectionFactory;
import jakarta.jms.Connection;
import java.util.HashMap;
import java.util.Map;

@RestController
public class JmsHealthController {
    
    @Autowired(required = false)
    private ConnectionFactory connectionFactory;
    
    @GetMapping("/jms-health")
    public Map<String, Object> checkJmsHealth() {
        Map<String, Object> health = new HashMap<>();
        
        if (connectionFactory == null) {
            health.put("status", "DISABLED");
            health.put("error", "ConnectionFactory not configured");
            return health;
        }
        
        try {
            try (Connection connection = connectionFactory.createConnection()) {
                connection.start();
                health.put("connectionFactory", connectionFactory.getClass().getSimpleName());
                health.put("status", "CONNECTED");
                health.put("timestamp", java.time.Instant.now());
            }
        } catch (Exception e) {
            health.put("status", "FAILED");
            health.put("error", e.getMessage());
        }
        
        return health;
    }
}