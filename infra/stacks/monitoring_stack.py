import aws_cdk as cdk
from constructs import Construct
from modules.monitoring import Monitoring

class MonitoringStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 app_runner_stack,
                 messaging_stack,
                 database_stack,
                 simple_websocket_stack,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get resource names from other stacks
        app_runner_service_name = app_runner_stack.app_runner.service.service_name
        app_runner_service_id = app_runner_stack.app_runner.service_id
        mq_broker_name = "spa-broker"  # From Messaging module
        dynamodb_table_name = database_stack.database.table.table_name
        lambda_function_name = simple_websocket_stack.simple_websocket.stream_processor.function_name
        websocket_api_id = simple_websocket_stack.simple_websocket.websocket_api.api_id
        
        # Create monitoring dashboards
        self.monitoring = Monitoring(
            self, "Monitoring",
            app_runner_service_name=app_runner_service_name,
            app_runner_service_id=app_runner_service_id,
            mq_broker_name=mq_broker_name,
            dynamodb_table_name=dynamodb_table_name,
            lambda_function_name=lambda_function_name,
            websocket_api_id=websocket_api_id
        )
        
        # Output dashboard URL
        cdk.CfnOutput(self, "DashboardUrl",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=reactive-messaging-app",
            description="CloudWatch Dashboard URL"
        )