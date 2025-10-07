package com.example.reactive;

import org.apache.activemq.ActiveMQConnectionFactory;
import org.apache.activemq.RedeliveryPolicy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jms.annotation.EnableJms;
import org.springframework.jms.config.DefaultJmsListenerContainerFactory;
import org.springframework.jms.core.JmsTemplate;
import org.springframework.util.ErrorHandler;
import org.springframework.beans.factory.annotation.Value;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import jakarta.jms.ConnectionFactory;
import jakarta.jms.Session;
import software.amazon.awssdk.services.secretsmanager.SecretsManagerClient;
import software.amazon.awssdk.services.secretsmanager.model.GetSecretValueRequest;
import software.amazon.awssdk.regions.Region;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Configuration
@EnableJms
public class JmsConfig {
    
    private static final Logger log = LoggerFactory.getLogger(JmsConfig.class);
    
    @Value("${aws.region:eu-west-2}")
    private String awsRegion;
    
    @Value("${mq.username.secret.name:MessagingStack-MessagingMqUsername}")
    private String usernameSecretName;
    
    @Value("${mq.password.secret.name:MessagingStack-MessagingMqPassword}")
    private String passwordSecretName;
    
    private String getMqCredential(String secretName, String credentialType) {
        try {
            SecretsManagerClient client = SecretsManagerClient.builder()
                .region(Region.of(awsRegion))
                .build();
            
            GetSecretValueRequest request = GetSecretValueRequest.builder()
                .secretId(secretName)
                .build();
            
            String secretValue = client.getSecretValue(request).secretString();
            ObjectMapper mapper = new ObjectMapper();
            JsonNode jsonNode = mapper.readTree(secretValue);
            
            String credential = jsonNode.get(credentialType).asText();
            log.info("Successfully retrieved MQ {} from Secrets Manager", credentialType);
            return credential;
        } catch (Exception e) {
            log.error("Failed to retrieve MQ {} from Secrets Manager: {}", credentialType, e.getMessage());
            throw new RuntimeException("Could not retrieve MQ " + credentialType, e);
        }
    }
    
    @Bean
    @Primary
    public ConnectionFactory connectionFactory() {
        String brokerUrl = System.getenv("MQ_BROKER_URL");
        if (brokerUrl == null || brokerUrl.isEmpty()) {
            throw new RuntimeException("MQ_BROKER_URL environment variable is required");
        }
        
        ActiveMQConnectionFactory factory = new ActiveMQConnectionFactory();
        factory.setBrokerURL(brokerUrl);
        factory.setUserName(getMqCredential(usernameSecretName, "username"));
        factory.setPassword(getMqCredential(passwordSecretName, "password"));
        factory.setTrustAllPackages(true);
        
        RedeliveryPolicy redeliveryPolicy = new RedeliveryPolicy();
        redeliveryPolicy.setMaximumRedeliveries(6);
        redeliveryPolicy.setInitialRedeliveryDelay(1000L);
        redeliveryPolicy.setRedeliveryDelay(2000L);
        redeliveryPolicy.setUseExponentialBackOff(true);
        redeliveryPolicy.setBackOffMultiplier(2.0);
        redeliveryPolicy.setMaximumRedeliveryDelay(30000L);
        
        factory.setRedeliveryPolicy(redeliveryPolicy);
        factory.setMessagePrioritySupported(true);
        
        log.info("Enhanced ConnectionFactory created with redelivery policy and priority support");
        return factory;
    }
    
    @Bean
    public DefaultJmsListenerContainerFactory jmsListenerContainerFactory(
        ConnectionFactory connectionFactory
    ) {
        DefaultJmsListenerContainerFactory factory = new DefaultJmsListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setSessionAcknowledgeMode(Session.CLIENT_ACKNOWLEDGE);
        factory.setErrorHandler(new EnhancedJmsErrorHandler());
        factory.setConcurrency("1-3");
        factory.setReceiveTimeout(1000L);
        factory.setRecoveryInterval(5000L);
        factory.setSessionTransacted(false);
        factory.setAutoStartup(true);
        
        log.info("Enhanced JmsListenerContainerFactory configured with CLIENT_ACKNOWLEDGE and priority support");
        return factory;
    }
    
    @Bean
    public JmsTemplate jmsTemplate(ConnectionFactory connectionFactory) {
        JmsTemplate jmsTemplate = new JmsTemplate(connectionFactory);
        jmsTemplate.setSessionAcknowledgeMode(Session.CLIENT_ACKNOWLEDGE);
        jmsTemplate.setDeliveryPersistent(true);
        jmsTemplate.setExplicitQosEnabled(true);
        jmsTemplate.setPriority(4); // Default medium priority
        
        log.info("JmsTemplate configured with priority support");
        return jmsTemplate;
    }
    
    public static class EnhancedJmsErrorHandler implements ErrorHandler {
        private static final Logger log = LoggerFactory.getLogger(EnhancedJmsErrorHandler.class);
        
        @Override
        public void handleError(Throwable t) {
            log.error("🚨 JMS ERROR: {}", t.getMessage(), t);
        }
    }
}