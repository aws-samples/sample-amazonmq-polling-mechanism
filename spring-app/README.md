# Spring Boot Reactive Application

## Features

- **DynamoDB Integration**: Saves items with same format as React app
- **Amazon MQ**: Sends messages to queue and processes them
- **Auto-update**: Updates lastModified timestamp when processing messages
- **App Runner**: Hosted on AWS App Runner for scalability

## Endpoints

- `POST /api/items` - Create custom item
- `POST /api/items/sample` - Create random sample item

## Local Development

```bash
# Build application
./build-spring.sh

# Run with Docker
docker run -p 8080:8080 reactive-spring-app
```

## AWS Deployment

The application is deployed via CDK with:
- **Amazon MQ**: Managed ActiveMQ broker
- **App Runner**: Serverless container hosting
- **Environment Variables**: Auto-configured from CDK

## Usage

```bash
# Create sample item (replace URL with App Runner URL)
curl -X POST https://your-app-runner-url/api/items/sample

# Create custom item
curl -X POST https://your-app-runner-url/api/items \
  -H "Content-Type: application/json" \
  -d '{"title":"Custom Task","message":"Test message","priority":"High","status":"Active"}'
```

## Flow

1. Item created via REST API
2. Saved to DynamoDB
3. Message sent to Amazon MQ queue
4. Message listener processes and updates lastModified timestamp
5. Changes visible in React app within 3 seconds