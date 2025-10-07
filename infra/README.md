# Modular CDK Infrastructure

## Structure

```
infra/
├── app.py              # CDK app entry point
├── spa_stack.py        # Main stack orchestrator
├── modules/            # Modular constructs
│   ├── spa_frontend.py # S3 + CloudFront
│   ├── database.py     # DynamoDB table
│   ├── auth.py         # Cognito + IAM
│   └── messaging.py    # Amazon MQ + VPC
└── requirements.txt    # Dependencies
```

## Modules

### 1. SpaFrontend (`modules/spa_frontend.py`)
- **S3 Bucket**: Private bucket for React build files
- **CloudFront**: CDN with Origin Access Identity
- **Error Handling**: SPA routing support (404 → index.html)

### 2. Database (`modules/database.py`)
- **DynamoDB Table**: NoSQL database with partition key "id"
- **Removal Policy**: Destroy on stack deletion

### 3. Auth (`modules/auth.py`)
- **Cognito Identity Pool**: Unauthenticated access
- **IAM Role**: DynamoDB permissions for React app
- **Permissions**: Scan, Put, Get, Query, Update operations

### 4. Messaging (`modules/messaging.py`)
- **VPC**: 2 AZ setup with public/isolated subnets
- **Security Groups**: ActiveMQ ports (61617, 8162)
- **Amazon MQ**: Single-instance ActiveMQ broker (mq.t3.micro)

## Benefits

✅ **Separation of Concerns**: Each module handles one responsibility
✅ **Reusability**: Modules can be used in other stacks
✅ **Maintainability**: Easier to update individual components
✅ **Testing**: Each module can be tested independently
✅ **Clear Dependencies**: Explicit parameter passing between modules

## Deployment

```bash
# Deploy all modules
cdk deploy

# Deploy specific changes
cdk diff
cdk deploy --require-approval never
```

## Outputs

- `BucketName`: S3 bucket for React app
- `DistributionDomainName`: CloudFront URL
- `IdentityPoolId`: Cognito Identity Pool
- `TableName`: DynamoDB table name
- `MqBrokerEndpoint`: Amazon MQ connection string
- `Region`: AWS region