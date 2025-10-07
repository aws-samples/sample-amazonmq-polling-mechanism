#!/bin/bash
set -e

echo "🚀 Starting Spring Boot application..."

# Get configuration from CDK outputs
cd infra
if [ -f "database-outputs.json" ] && [ -f "messaging-outputs.json" ]; then
    TABLE_NAME=$(cat database-outputs.json | grep -o '"TableName": "[^"]*"' | cut -d'"' -f4)
    MQ_BROKER_ID=$(cat messaging-outputs.json | grep -o '"MqBrokerId": "[^"]*"' | cut -d'"' -f4)
    
    echo "📝 Table: $TABLE_NAME"
    echo "📝 MQ Broker: $MQ_BROKER_ID"
    
    # Get MQ broker endpoint from AWS
    MQ_ENDPOINT=$(aws mq describe-broker --broker-id "$MQ_BROKER_ID" --query 'BrokerInstances[0].Endpoints[0]' --output text 2>/dev/null || echo "")
    
    if [ -n "$MQ_ENDPOINT" ] && [ "$MQ_ENDPOINT" != "None" ]; then
        # Use SSL endpoint as-is for Amazon MQ
        export MQ_BROKER_URL="$MQ_ENDPOINT"
        echo "🔗 Using Amazon MQ: $MQ_ENDPOINT"
    else
        export MQ_BROKER_URL="tcp://localhost:61616"
        echo "⚠️  Amazon MQ not accessible, using local ActiveMQ"
        echo "   Make sure local ActiveMQ is running on port 61616"
    fi
    
    # Set other environment variables
    export DYNAMODB_TABLE_NAME="$TABLE_NAME"
    export AWS_REGION="eu-west-2"
    
    echo "⚙️ Environment configured"
else
    echo "❌ CDK outputs not found. Run ./deploy.sh first."
    exit 1
fi

# Start Spring Boot
cd ../spring-app
echo "🔨 Building application..."
mvn compile -q

echo "🚀 Starting Spring Boot on http://localhost:8080"
echo "📋 API Endpoints:"
echo "   POST http://localhost:8080/api/items/sample"
echo "   POST http://localhost:8080/api/items"
echo ""

mvn spring-boot:run