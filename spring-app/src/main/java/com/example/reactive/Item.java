package com.example.reactive;

import com.fasterxml.jackson.annotation.JsonProperty;

public class Item {
    private String id;
    private String title;
    private String message;
    private String priority;
    private String status;
    private Long timestamp;
    private String createdAt;
    private String lastModified;
    private int delay;

    public Item() {}

    public Item(String id, String title, String message, String priority, String status) {
        this.id = id;
        this.title = title;
        this.message = message;
        this.priority = priority;
        this.status = status;
        this.timestamp = System.currentTimeMillis();
        this.createdAt = java.time.Instant.now().toString();
        this.lastModified = "";
        this.delay = 0;
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public String getPriority() { return priority; }
    public void setPriority(String priority) { this.priority = priority; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Long getTimestamp() { return timestamp; }
    public void setTimestamp(Long timestamp) { this.timestamp = timestamp; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public String getLastModified() { return lastModified; }
    public void setLastModified(String lastModified) { this.lastModified = lastModified; }

    public int getDelay() { return delay; }
    public void setDelay(int delay) { this.delay = delay; }

    public void updateModified() {
        this.lastModified = java.time.Instant.now().toString();
    }
}