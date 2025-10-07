/*
 * Copyright (c) 2025 AWS Prescriptive Architecture: Priority-Based Message Processing
 * Licensed under the MIT License. See LICENSE file in the project root.
 */

package com.example.reactive;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.jms.annotation.EnableJms;
import org.springframework.retry.annotation.EnableRetry;

@SpringBootApplication
@EnableJms
@EnableRetry
public class ReactiveApplication {
    public static void main(String[] args) {
        SpringApplication.run(ReactiveApplication.class, args);
    }
}