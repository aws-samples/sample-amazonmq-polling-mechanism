#!/bin/bash
# Copyright (c) 2025 AWS Prescriptive Architecture: Priority-Based Message Processing
# Licensed under the MIT License. See LICENSE file in the project root.
# Configuration file for the messaging application

# Default values - can be overridden by environment variables
export AWS_REGION=${AWS_REGION:-"ap-southeast-2"}
export REPO_NAME=${REPO_NAME:-"reactive-spring-app"}
export APP_NAME=${APP_NAME:-"reactive-messaging-app"}

# CDK App configuration
export CDK_APP="python3 app_modular.py"

# Stack deployment order
export STACK_ORDER="FrontendStack DatabaseStack AuthStack VPCStack MessagingStack AppRunnerStack SimpleWebSocketStack MonitoringStack"

# Stack destruction order (reverse of deployment)
export DESTROY_ORDER="MonitoringStack SimpleWebSocketStack AppRunnerStack MessagingStack VPCStack AuthStack DatabaseStack FrontendStack"

echo "📋 Configuration loaded:"
echo "   Region: $AWS_REGION"
echo "   Repository: $REPO_NAME"
echo "   App Name: $APP_NAME"