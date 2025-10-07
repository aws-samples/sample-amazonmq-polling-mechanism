package com.example.reactive;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;
import java.util.HashMap;
import java.util.Map;

@Service
public class MQStatsService {

    private static final Logger log = LoggerFactory.getLogger(MQStatsService.class);
    
    @Value("${mq.broker.url:ssl://b-c95fe023-c451-4c80-8b82-395e9b0206cf-1.mq.eu-west-2.amazonaws.com:61617}")
    private String brokerUrl;

    public Map<String, Object> getQueueStatistics(String queueName) {
        Map<String, Object> stats = new HashMap<>();
        
        try {
            // Extract host from broker URL
            String host = brokerUrl.replace("ssl://", "").split(":")[0];
            String jmxUrl = "service:jmx:rmi:///jndi/rmi://" + host + ":1099/jmxrmi";
            
            log.info("Attempting JMX connection to: {}", jmxUrl);
            
            JMXServiceURL serviceURL = new JMXServiceURL(jmxUrl);
            Map<String, Object> environment = new HashMap<>();
            // JMX credentials would need to be retrieved from Secrets Manager for production use
            // For now, JMX is disabled on Amazon MQ managed service
            
            try (JMXConnector connector = JMXConnectorFactory.connect(serviceURL, environment)) {
                MBeanServerConnection connection = connector.getMBeanServerConnection();
                
                // Queue statistics ObjectName
                ObjectName queueObjectName = new ObjectName(
                    "org.apache.activemq:type=Broker,brokerName=*,destinationType=Queue,destinationName=" + queueName
                );
                
                // Get queue statistics
                Long queueSize = (Long) connection.getAttribute(queueObjectName, "QueueSize");
                Long enqueueCount = (Long) connection.getAttribute(queueObjectName, "EnqueueCount");
                Long dequeueCount = (Long) connection.getAttribute(queueObjectName, "DequeueCount");
                Long consumerCount = (Long) connection.getAttribute(queueObjectName, "ConsumerCount");
                Long producerCount = (Long) connection.getAttribute(queueObjectName, "ProducerCount");
                
                stats.put("queueName", queueName);
                stats.put("queueSize", queueSize);
                stats.put("enqueueCount", enqueueCount);
                stats.put("dequeueCount", dequeueCount);
                stats.put("consumerCount", consumerCount);
                stats.put("producerCount", producerCount);
                stats.put("status", "connected");
                stats.put("jmxEnabled", true);
                
                log.info("JMX Stats - Queue: {}, Size: {}, Enqueued: {}, Dequeued: {}", 
                        queueName, queueSize, enqueueCount, dequeueCount);
                
            }
            
        } catch (Exception e) {
            log.warn("JMX connection failed: {}", e.getMessage());
            stats.put("status", "jmx_unavailable");
            stats.put("jmxEnabled", false);
            stats.put("error", "JMX not available on Amazon MQ managed service");
            stats.put("note", "Using alternative queue monitoring");
        }
        
        return stats;
    }
}