package com.example.reactive;

import org.springframework.stereotype.Service;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.*;
import java.util.HashMap;
import java.util.Map;

@Service
public class DynamoService {
    
    private final DynamoDbClient dynamoDbClient;
    private final String tableName;

    public DynamoService(DynamoDbClient dynamoDbClient) {
        this.dynamoDbClient = dynamoDbClient;
        this.tableName = System.getenv().getOrDefault("DYNAMODB_TABLE_NAME", "SpaStack-SpaTable64AC937B-U6LZU789SYMH");
    }



    public Item getItem(String id) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s(id).build());
        
        GetItemRequest request = GetItemRequest.builder()
                .tableName(tableName)
                .key(key)
                .build();
                
        GetItemResponse response = dynamoDbClient.getItem(request);
        
        if (!response.hasItem()) {
            throw new RuntimeException("Item not found: " + id);
        }
        
        Map<String, AttributeValue> itemMap = response.item();
        Item item = new Item();
        item.setId(itemMap.get("id").s());
        item.setTitle(itemMap.get("title").s());
        item.setMessage(itemMap.get("message").s());
        item.setPriority(itemMap.get("priority").s());
        item.setStatus(itemMap.get("status").s());
        item.setTimestamp(Long.parseLong(itemMap.get("timestamp").n()));
        item.setCreatedAt(itemMap.get("createdAt").s());
        AttributeValue lastModifiedAttr = itemMap.get("lastModified");
        item.setLastModified(lastModifiedAttr != null ? lastModifiedAttr.s() : "");
        item.setDelay(Integer.parseInt(itemMap.get("delay").n()));
        
        return item;
    }
    
    public void createItem(Item item) {
        putItem(item);
    }

    public void putItem(Item item) {
        Map<String, AttributeValue> itemMap = new HashMap<>();
        itemMap.put("id", AttributeValue.builder().s(item.getId()).build());
        itemMap.put("title", AttributeValue.builder().s(item.getTitle()).build());
        itemMap.put("message", AttributeValue.builder().s(item.getMessage()).build());
        itemMap.put("priority", AttributeValue.builder().s(item.getPriority()).build());
        itemMap.put("status", AttributeValue.builder().s(item.getStatus()).build());
        itemMap.put("timestamp", AttributeValue.builder().n(item.getTimestamp().toString()).build());
        itemMap.put("createdAt", AttributeValue.builder().s(item.getCreatedAt()).build());
        String lastModified = item.getLastModified();
        if (lastModified != null && !lastModified.isEmpty() && !"N/A".equals(lastModified)) {
            itemMap.put("lastModified", AttributeValue.builder().s(lastModified).build());
        }
        itemMap.put("delay", AttributeValue.builder().n(String.valueOf(item.getDelay())).build());

        PutItemRequest request = PutItemRequest.builder()
                .tableName(tableName)
                .item(itemMap)
                .build();

        dynamoDbClient.putItem(request);
    }

    public void updateItemModified(String id) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s(id).build());

        Map<String, AttributeValueUpdate> updates = new HashMap<>();
        updates.put("lastModified", AttributeValueUpdate.builder()
                .value(AttributeValue.builder().s(java.time.Instant.now().toString()).build())
                .action(AttributeAction.PUT)
                .build());

        UpdateItemRequest request = UpdateItemRequest.builder()
                .tableName(tableName)
                .key(key)
                .attributeUpdates(updates)
                .build();

        dynamoDbClient.updateItem(request);
    }

    public void updateItemStatus(String id, String status) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s(id).build());

        Map<String, AttributeValueUpdate> updates = new HashMap<>();
        updates.put("status", AttributeValueUpdate.builder()
                .value(AttributeValue.builder().s(status).build())
                .action(AttributeAction.PUT)
                .build());

        UpdateItemRequest request = UpdateItemRequest.builder()
                .tableName(tableName)
                .key(key)
                .attributeUpdates(updates)
                .build();

        dynamoDbClient.updateItem(request);
    }
    
    public void deleteItem(String id) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s(id).build());
        
        DeleteItemRequest request = DeleteItemRequest.builder()
                .tableName(tableName)
                .key(key)
                .build();
                
        dynamoDbClient.deleteItem(request);
    }
    
    public int deleteAllItems() {
        try {
            ScanRequest scanRequest = ScanRequest.builder()
                    .tableName(tableName)
                    .build();
                    
            ScanResponse scanResponse = dynamoDbClient.scan(scanRequest);
            int deletedCount = 0;
            
            for (Map<String, AttributeValue> item : scanResponse.items()) {
                String id = item.get("id").s();
                deleteItem(id);
                deletedCount++;
            }
            
            return deletedCount;
        } catch (Exception e) {
            throw new RuntimeException("Failed to delete all items", e);
        }
    }
}