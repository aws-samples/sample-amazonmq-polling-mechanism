package com.example.reactive;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.jms.config.JmsListenerEndpointRegistry;
import org.springframework.jms.listener.MessageListenerContainer;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import jakarta.jms.ConnectionFactory;
import org.springframework.jms.config.DefaultJmsListenerContainerFactory;
import org.springframework.jms.listener.DefaultMessageListenerContainer;
import java.util.*;

@RestController
public class JmsDebugController {
    
    @Autowired(required = false)
    private JmsListenerEndpointRegistry jmsListenerEndpointRegistry;
    
    @Autowired
    private ApplicationContext applicationContext;
    
    @GetMapping("/jms-debug")
    public Map<String, Object> debugJmsConfiguration() {
        Map<String, Object> debug = new HashMap<>();
        
        if (jmsListenerEndpointRegistry != null) {
            Collection<String> listenerIds = jmsListenerEndpointRegistry.getListenerContainerIds();
            debug.put("registeredListeners", listenerIds);
            debug.put("listenerCount", listenerIds.size());
            
            Map<String, Object> containerDetails = new HashMap<>();
            for (String id : listenerIds) {
                MessageListenerContainer container = jmsListenerEndpointRegistry.getListenerContainer(id);
                if (container != null) {
                    Map<String, Object> containerInfo = new HashMap<>();
                    containerInfo.put("running", container.isRunning());
                    containerInfo.put("autoStartup", container.isAutoStartup());
                    containerInfo.put("containerType", container.getClass().getSimpleName());
                    
                    // Enhanced details for DefaultMessageListenerContainer
                    if (container instanceof org.springframework.jms.listener.DefaultMessageListenerContainer) {
                        org.springframework.jms.listener.DefaultMessageListenerContainer dmlc = 
                            (org.springframework.jms.listener.DefaultMessageListenerContainer) container;
                        
                        containerInfo.put("sessionAcknowledgeMode", getAcknowledgeModeString(dmlc.getSessionAcknowledgeMode()));
                        containerInfo.put("sessionTransacted", dmlc.isSessionTransacted());
                        containerInfo.put("maxConcurrentConsumers", dmlc.getMaxConcurrentConsumers());
                        containerInfo.put("activeConsumerCount", dmlc.getActiveConsumerCount());
                        containerInfo.put("scheduledConsumerCount", dmlc.getScheduledConsumerCount());
                        containerInfo.put("destinationName", dmlc.getDestinationName());
                    }
                    
                    containerDetails.put(id, containerInfo);
                }
            }
            debug.put("containerDetails", containerDetails);
        } else {
            debug.put("error", "JmsListenerEndpointRegistry not found");
        }
        
        // Connection Factory details
        try {
            ConnectionFactory cf = applicationContext.getBean(ConnectionFactory.class);
            Map<String, Object> cfInfo = new HashMap<>();
            cfInfo.put("type", cf.getClass().getSimpleName());
            
            if (cf instanceof org.apache.activemq.ActiveMQConnectionFactory) {
                org.apache.activemq.ActiveMQConnectionFactory amqCf = (org.apache.activemq.ActiveMQConnectionFactory) cf;
                cfInfo.put("brokerURL", amqCf.getBrokerURL());
                cfInfo.put("userName", amqCf.getUserName());
                cfInfo.put("trustAllPackages", amqCf.isTrustAllPackages());
                
                if (amqCf.getRedeliveryPolicy() != null) {
                    Map<String, Object> redeliveryInfo = new HashMap<>();
                    redeliveryInfo.put("maximumRedeliveries", amqCf.getRedeliveryPolicy().getMaximumRedeliveries());
                    redeliveryInfo.put("initialRedeliveryDelay", amqCf.getRedeliveryPolicy().getInitialRedeliveryDelay());
                    redeliveryInfo.put("useExponentialBackOff", amqCf.getRedeliveryPolicy().isUseExponentialBackOff());
                    redeliveryInfo.put("backOffMultiplier", amqCf.getRedeliveryPolicy().getBackOffMultiplier());
                    cfInfo.put("redeliveryPolicy", redeliveryInfo);
                }
            }
            debug.put("connectionFactoryDetails", cfInfo);
        } catch (Exception e) {
            debug.put("connectionFactoryError", e.getMessage());
        }
        
        // Bean names
        String[] jmsRelatedBeans = applicationContext.getBeanNamesForType(ConnectionFactory.class);
        debug.put("connectionFactoryBeans", Arrays.asList(jmsRelatedBeans));
        
        String[] containerFactoryBeans = applicationContext.getBeanNamesForType(DefaultJmsListenerContainerFactory.class);
        debug.put("containerFactoryBeans", Arrays.asList(containerFactoryBeans));
        
        // Spring Retry status
        debug.put("springRetryEnabled", applicationContext.containsBean("retryTemplate"));
        
        // Current timestamp
        debug.put("timestamp", java.time.Instant.now());
        
        return debug;
    }
    
    private String getAcknowledgeModeString(int mode) {
        switch (mode) {
            case 1: return "AUTO_ACKNOWLEDGE";
            case 2: return "CLIENT_ACKNOWLEDGE";
            case 3: return "DUPS_OK_ACKNOWLEDGE";
            case 0: return "SESSION_TRANSACTED";
            default: return "UNKNOWN(" + mode + ")";
        }
    }
}