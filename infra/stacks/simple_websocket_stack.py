from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_lambda_event_sources as event_sources
from aws_cdk import aws_lambda as lambda_
from constructs import Construct
from modules.simple_websocket import SimpleWebSocket
from cdk_nag import NagSuppressions

class SimpleWebSocketStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, database_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add dependency
        self.add_dependency(database_stack)

        # Create simple WebSocket
        self.simple_websocket = SimpleWebSocket(
            self, "SimpleWebSocket",
            table_name=database_stack.database.table.table_name
        )
        
        # Add DynamoDB Stream trigger
        self.simple_websocket.stream_processor.add_event_source(
            event_sources.DynamoEventSource(database_stack.database.table,
                starting_position=lambda_.StartingPosition.LATEST,
                batch_size=10
            )
        )

        # Add CDK-nag suppression for DefaultPolicy at stack level
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/SimpleWebSocketStack/SimpleWebSocket/StreamProcessorRole/DefaultPolicy/Resource",
            [{"id": "AwsSolutions-IAM5", "reason": "Lambda execution role requires wildcard permissions for CloudWatch Logs", "appliesTo": ["Resource::*"]}]
        )

        # Outputs
        CfnOutput(self, "SimpleWebSocketURL", value=self.simple_websocket.websocket_url)
        CfnOutput(self, "SimpleWebSocketAPIId", value=self.simple_websocket.websocket_api.api_id)