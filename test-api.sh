#!/bin/bash
# Copyright (c) 2025 AWS Prescriptive Architecture: Priority-Based Message Processing
# Licensed under the MIT License. See LICENSE file in the project root.
set -e

# Usage: ./test-api.sh [delay] [title] [message] [priority] [status]
# Examples:
#   ./test-api.sh 5
#   ./test-api.sh 15 "Custom Task" "Custom message"
#   ./test-api.sh 0 "Immediate Task" "No delay" "High" "Active"
#   ./test-api.sh --incremental    # Creates 15 messages with 1-15s delays

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [delay] [title] [message] [priority] [status]"
    echo ""
    echo "Parameters:"
    echo "  delay     - Delay in seconds (default: 10)"
    echo "  title     - Task title (default: 'Delayed Task')"
    echo "  message   - Task message (default: '{delay} second delay processing')"
    echo "  priority  - Priority level (default: 'Medium')"
    echo "  status    - Task status (default: 'Pending')"
    echo ""
    echo "Examples:"
    echo "  $0 5"
    echo "  $0 15 'Custom Task' 'Custom message'"
    echo "  $0 0 'Immediate Task' 'No delay' 'High' 'Active'"
    echo "  $0 --incremental    # Creates 15 messages with 1-15s delays"
    echo "  $0 -i               # Same as --incremental"
    exit 0
fi

# Get AppRunner Service URL dynamically
if [ -f "infra/apprunner-outputs.json" ]; then
    API_URL=$(cat infra/apprunner-outputs.json | grep -o '"ServiceUrl": "[^"]*"' | tail -1 | cut -d'"' -f4)
elif [ -f "infra/outputs.json" ]; then
    API_URL=$(cat infra/outputs.json | grep -o '"ServiceUrl": "[^"]*"' | tail -1 | cut -d'"' -f4)
else
    # Get from AWS CLI if outputs file doesn't exist
    REGION="ap-southeast-2"
    SERVICE_URL=$(aws apprunner list-services --region $REGION --query 'ServiceSummaryList[?ServiceName==`reactive-spring-app`].ServiceUrl' --output text 2>/dev/null || echo "")
    if [ -n "$SERVICE_URL" ] && [ "$SERVICE_URL" != "None" ]; then
        API_URL="$SERVICE_URL"
    else
        # Fallback to the current ap-south-1 endpoint from deployment
        API_URL="https://smuxuxvipp.ap-south-1.awsapprunner.com"
        echo "⚠️  Using fallback API URL for ap-south-1"
    fi
fi

if [ -z "$API_URL" ]; then
    echo "❌ Could not extract API URL from outputs"
    exit 1
fi

# Ensure API URL has https prefix
if [[ ! "$API_URL" =~ ^https?:// ]]; then
    API_URL="https://$API_URL"
fi

# Check if incremental mode is requested
if [ "$1" = "--incremental" ] || [ "$1" = "-i" ]; then
    echo "🔄 Creating incremental test messages (1-15 second delays)"
    echo ""
    
    for delay in $(seq 1 15); do
        echo "📝 Creating message with ${delay}s delay..."
        
        curl -X POST "$API_URL/api/items" \
          -H "Content-Type: application/json" \
          -d "{\"title\": \"Incremental Test ${delay}\", \"message\": \"${delay} second delay test\", \"priority\": \"Medium\", \"status\": \"Pending\", \"delay\": $delay}" \
          --silent > /dev/null
        
        echo "✅ Message ${delay}/15 created"
        sleep 0.5  # Small delay between requests
    done
    
    echo ""
    echo "🎉 All 15 incremental messages created!"
    echo "📊 Check the MQ panel to see the queue activity"
    exit 0
fi

# Default values for single message mode
DELAY=${1:-10}
TITLE=${2:-"Delayed Task"}
MESSAGE=${3:-"${DELAY} second delay processing"}
PRIORITY=${4:-"Medium"}
STATUS=${5:-"Pending"}

# API URL already set above

echo "🧪 Testing API at: $API_URL"
echo "📝 Creating item with ${DELAY}s delay"
echo "   Title: $TITLE"
echo "   Message: $MESSAGE"
echo "   Priority: $PRIORITY"
echo "   Status: $STATUS"
echo ""

curl -X POST "$API_URL/api/items" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"$TITLE\", \"message\": \"$MESSAGE\", \"priority\": \"$PRIORITY\", \"status\": \"$STATUS\", \"delay\": $DELAY}"

echo -e "\n✅ Test completed!"