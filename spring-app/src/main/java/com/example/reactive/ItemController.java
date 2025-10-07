package com.example.reactive;

import org.springframework.web.bind.annotation.*;
import java.util.Random;

@RestController
@RequestMapping("/api/items")
public class ItemController {

    private final DynamoService dynamoService;
    private final MessageService messageService;
    private final Random random = new Random();

    public ItemController(DynamoService dynamoService, MessageService messageService) {
        this.dynamoService = dynamoService;
        this.messageService = messageService;
    }

    @PostMapping
    public Item createItem(@RequestBody Item item) {
        // Set ID if not provided
        if (item.getId() == null) {
            item.setId("spring-" + System.currentTimeMillis());
        }
        
        // Set timestamp and dates
        item.setTimestamp(System.currentTimeMillis());
        item.setCreatedAt(java.time.Instant.now().toString());
        
        // Set lastModified based on delay
        if (item.getDelay() > 0) {
            item.setLastModified("N/A"); // N/A for delayed items
        } else {
            item.setLastModified("");
        }

        // Save to DynamoDB
        dynamoService.putItem(item);
        
        // Send to queue
        messageService.sendMessage(item);
        
        return item;
    }

    @PostMapping("/sample")
    public Item createSampleItem() {
        String[] priorities = {"High", "Medium", "Low"};
        String[] statuses = {"Active", "Pending", "Completed"};
        String[] types = {"Task", "Bug", "Feature", "Issue"};

        String type = types[random.nextInt(types.length)];
        String priority = priorities[random.nextInt(priorities.length)];
        String status = statuses[random.nextInt(statuses.length)];

        Item item = new Item(
            "spring-" + System.currentTimeMillis(),
            type + " #" + random.nextInt(1000),
            "Spring Boot item created at " + java.time.Instant.now(),
            priority,
            status
        );
        item.setDelay(random.nextInt(10));

        dynamoService.putItem(item);
        messageService.sendMessage(item);
        
        return item;
    }
    
    @DeleteMapping("/{id}")
    @CrossOrigin(origins = "*")
    public java.util.Map<String, Object> deleteItem(@PathVariable String id) {
        try {
            System.out.println("Deleting item with ID: " + id);
            dynamoService.deleteItem(id);
            System.out.println("Item deleted successfully: " + id);
            
            return java.util.Map.of(
                "status", "success",
                "message", "Item deleted successfully",
                "id", id,
                "timestamp", java.time.Instant.now()
            );
        } catch (Exception e) {
            System.out.println("Error deleting item: " + e.getMessage());
            return java.util.Map.of(
                "status", "error",
                "message", e.getMessage(),
                "id", id
            );
        }
    }
    
    @DeleteMapping("/delete-all")
    @CrossOrigin(origins = "*")
    public java.util.Map<String, Object> deleteAllItems() {
        try {
            int deletedCount = dynamoService.deleteAllItems();
            
            return java.util.Map.of(
                "status", "success",
                "message", "All items deleted successfully",
                "deletedCount", deletedCount,
                "timestamp", java.time.Instant.now()
            );
        } catch (Exception e) {
            return java.util.Map.of(
                "status", "error",
                "message", e.getMessage()
            );
        }
    }
}