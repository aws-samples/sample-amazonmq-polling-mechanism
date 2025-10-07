#!/usr/bin/env python3
# Copyright (c) 2025 AWS Prescriptive Architecture: Priority-Based Message Processing
# Licensed under the MIT License. See LICENSE file in the project root.

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from stacks.frontend_stack import FrontendStack
from stacks.database_stack import DatabaseStack
from stacks.auth_stack import AuthStack
from stacks.vpc_stack import VPCStack
from stacks.messaging_stack import MessagingStack
from stacks.ecr_stack import ECRStack
from stacks.apprunner_stack import AppRunnerStack
from stacks.simple_websocket_stack import SimpleWebSocketStack
from stacks.monitoring_stack import MonitoringStack

app = cdk.App()

# Add cdk-nag checks (optional - can be disabled with context flag)
if app.node.try_get_context("enable-nag") != "false":
    cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Deploy stacks in order
frontend_stack = FrontendStack(app, "FrontendStack")
database_stack = DatabaseStack(app, "DatabaseStack")
auth_stack = AuthStack(app, "AuthStack")
vpc_stack = VPCStack(app, "VPCStack")
messaging_stack = MessagingStack(app, "MessagingStack", vpc_stack)
ecr_stack = ECRStack(app, "ECRStack")
app_runner_stack = AppRunnerStack(app, "AppRunnerStack", 
    database_stack=database_stack,
    messaging_stack=messaging_stack,
    vpc_stack=vpc_stack)

simple_websocket_stack = SimpleWebSocketStack(app, "SimpleWebSocketStack", database_stack)

# Monitoring stack (depends on all other stacks)
monitoring_stack = MonitoringStack(app, "MonitoringStack",
    app_runner_stack=app_runner_stack,
    messaging_stack=messaging_stack,
    database_stack=database_stack,
    simple_websocket_stack=simple_websocket_stack
)

app.synth()