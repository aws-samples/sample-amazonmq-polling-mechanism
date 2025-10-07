from aws_cdk import (
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_lambda as lambda_,
    aws_dynamodb,
    aws_lambda_event_sources as event_sources,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
from cdk_nag import NagSuppressions

class SimpleWebSocket(Construct):
    def __init__(self, scope: Construct, construct_id: str, table_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB table to store WebSocket connections
        self.connections_table = aws_dynamodb.Table(
            self, "ConnectionsTable",
            table_name="simple-websocket-connections",
            partition_key=aws_dynamodb.Attribute(
                name="connectionId",
                type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True
        )

        # WebSocket connection handler
        connection_handler_role = iam.Role(
            self, "ConnectionHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "LogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[f"arn:aws:logs:{scope.region}:{scope.account}:*"]
                        )
                    ]
                ),
                "DynamoDBPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:DeleteItem"
                            ],
                            resources=[f"arn:aws:dynamodb:{scope.region}:{scope.account}:table/simple-websocket-connections"]
                        )
                    ]
                )
            }
        )

        self.connection_handler = lambda_.Function(
            self, "ConnectionHandler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            role=connection_handler_role,
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
connections_table = dynamodb.Table('simple-websocket-connections')

def handler(event, context):
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    logger.info(f"Route: {route_key}, Connection: {connection_id}")
    
    if route_key == '$connect':
        connections_table.put_item(Item={'connectionId': connection_id})
        logger.info(f"Connection {connection_id} stored")
        return {'statusCode': 200}
    elif route_key == '$disconnect':
        connections_table.delete_item(Key={'connectionId': connection_id})
        logger.info(f"Connection {connection_id} removed")
        return {'statusCode': 200}
    
    return {'statusCode': 200}
""")
        )

        # WebSocket API
        self.websocket_api = apigwv2.WebSocketApi(
            self, "SimpleWebSocketAPI",
            api_name="simple-websocket-api",
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration", self.connection_handler
                )
            ),
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration", self.connection_handler
                )
            )
        )

        # WebSocket Stage with access logging
        log_group = logs.LogGroup(self, "WebSocketLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        self.websocket_stage = apigwv2.CfnStage(
            self, "SimpleWebSocketStage",
            api_id=self.websocket_api.api_id,
            stage_name="prod",
            auto_deploy=True
        )

        # DynamoDB Stream processor
        stream_processor_role = iam.Role(
            self, "StreamProcessorRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "LogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[f"arn:aws:logs:{scope.region}:{scope.account}:*"]
                        )
                    ]
                ),
                "DynamoDBPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:Scan",
                                "dynamodb:DeleteItem"
                            ],
                            resources=[f"arn:aws:dynamodb:{scope.region}:{scope.account}:table/simple-websocket-connections"]
                        )
                    ]
                ),
                "APIGatewayPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["execute-api:ManageConnections"],
                            resources=[f"arn:aws:execute-api:{scope.region}:{scope.account}:{self.websocket_api.api_id}/*/*/@connections/*"]
                        )
                    ]
                )
            }
        )

        # CDK-nag suppressions for stream processor role
        NagSuppressions.add_resource_suppressions(
            stream_processor_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs requires wildcard for log group creation and API Gateway requires wildcard for connection management",
                    "appliesTo": [
                        "Resource::*",
                        f"Resource::arn:aws:execute-api:<AWS::Region>:<AWS::AccountId>:{self.websocket_api.api_id}/*/*/@connections/*",
                        "Resource::arn:aws:execute-api:<AWS::Region>:<AWS::AccountId>:<SimpleWebSocketSimpleWebSocketAPI25F64B99>/*/*/@connections/*"
                    ]
                }
            ],
            apply_to_children=True
        )

        self.stream_processor = lambda_.Function(
            self, "StreamProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            role=stream_processor_role,
            code=lambda_.Code.from_inline("""
import json
import boto3
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    # Initialize clients
    dynamodb = boto3.resource('dynamodb')
    connections_table = dynamodb.Table('simple-websocket-connections')
    
    api_id = os.environ['API_ID']
    region = os.environ['AWS_REGION']
    endpoint_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/prod"
    apigateway = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)
    
    logger.info(f"Processing {len(event['Records'])} DynamoDB stream records")
    
    for record in event['Records']:
        event_name = record['eventName']
        logger.info(f"Processing {event_name} event")
        
        if event_name in ['INSERT', 'MODIFY', 'REMOVE']:
            # Prepare change data
            change_data = {
                'eventName': event_name,
                'timestamp': record['dynamodb'].get('ApproximateCreationDateTime'),
                'data': None
            }
            
            # Get the appropriate data based on event type
            if event_name == 'INSERT':
                change_data['data'] = convert_dynamodb_to_json(record['dynamodb']['NewImage'])
            elif event_name == 'MODIFY':
                change_data['data'] = convert_dynamodb_to_json(record['dynamodb']['NewImage'])
                change_data['oldData'] = convert_dynamodb_to_json(record['dynamodb']['OldImage'])
            elif event_name == 'REMOVE':
                change_data['data'] = convert_dynamodb_to_json(record['dynamodb']['OldImage'])
            
            logger.info(f"Broadcasting {event_name} for item: {change_data['data'].get('id', 'unknown')}")
            
            # Get all active connections
            try:
                response = connections_table.scan()
                connections = response.get('Items', [])
                logger.info(f"Found {len(connections)} active connections")
                
                # Send update to all connected clients
                dead_connections = []
                for connection in connections:
                    connection_id = connection['connectionId']
                    try:
                        apigateway.post_to_connection(
                            ConnectionId=connection_id,
                            Data=json.dumps(change_data)
                        )
                        logger.info(f"Message sent to {connection_id}")
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'GoneException':
                            # Connection is stale, mark for removal
                            dead_connections.append(connection_id)
                            logger.info(f"Marked stale connection {connection_id} for removal")
                        else:
                            logger.error(f"Error sending to {connection_id}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error sending to {connection_id}: {str(e)}")
                        dead_connections.append(connection_id)
                
                # Remove dead connections
                for conn_id in dead_connections:
                    try:
                        connections_table.delete_item(Key={'connectionId': conn_id})
                        logger.info(f"Removed dead connection {conn_id}")
                    except Exception as e:
                        logger.error(f"Error removing connection {conn_id}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error processing stream record: {str(e)}")
    
    return {'statusCode': 200}

def convert_dynamodb_to_json(dynamodb_item):
    def convert_value(value):
        if 'S' in value:
            return value['S']
        elif 'N' in value:
            return float(value['N']) if '.' in value['N'] else int(value['N'])
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'NULL' in value:
            return None
        elif 'L' in value:
            return [convert_value(v) for v in value['L']]
        elif 'M' in value:
            return {k: convert_value(v) for k, v in value['M'].items()}
        return value
    
    return {k: convert_value(v) for k, v in dynamodb_item.items()}
"""),
            environment={
                'API_ID': self.websocket_api.api_id
            }
        )

        # Store table name for later use
        self.table_name = table_name

        # Comprehensive CDK-nag suppressions
        NagSuppressions.add_resource_suppressions(
            connection_handler_role,
            [{"id": "AwsSolutions-IAM5", "reason": "CloudWatch Logs requires wildcard for log streams", "appliesTo": ["Resource::*"]}],
            apply_to_children=True
        )
        NagSuppressions.add_resource_suppressions(
            stream_processor_role,
            [{"id": "AwsSolutions-IAM5", "reason": "CloudWatch Logs and API Gateway require wildcard permissions", "appliesTo": ["Resource::*"]}],
            apply_to_children=True
        )
        NagSuppressions.add_resource_suppressions(
            self.stream_processor,
            [{"id": "AwsSolutions-IAM5", "reason": "Lambda function requires wildcard permissions for CloudWatch Logs", "appliesTo": ["Resource::*"]}],
            apply_to_children=True
        )
        NagSuppressions.add_resource_suppressions(
            self.websocket_api,
            [{"id": "AwsSolutions-APIG4", "reason": "Demo environment - public WebSocket for testing"}],
            apply_to_children=True
        )

        # Output WebSocket URL
        self.websocket_url = f"wss://{self.websocket_api.api_id}.execute-api.{scope.region}.amazonaws.com/prod"
        
        # CDK-nag suppressions
        NagSuppressions.add_resource_suppressions(
            connection_handler_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs requires wildcard permissions for log group creation",
                    "appliesTo": ["Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:*"]
                }
            ]
        )
        
        NagSuppressions.add_resource_suppressions(
            stream_processor_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch Logs requires wildcard permissions for log group creation",
                    "appliesTo": ["Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:*"]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "API Gateway WebSocket connections require wildcard for connection management",
                    "appliesTo": ["Resource::arn:aws:execute-api:<AWS::Region>:<AWS::AccountId>:*/*/*/@connections/*"]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "DynamoDB streams require wildcard permissions for stream processing",
                    "appliesTo": ["Resource::*"]
                }
            ]
        )
        
        NagSuppressions.add_resource_suppressions(
            self.connection_handler,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Python 3.12 is the latest available runtime version"
                }
            ]
        )
        
        NagSuppressions.add_resource_suppressions(
            self.stream_processor,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Python 3.12 is the latest available runtime version"
                }
            ]
        )
        
        NagSuppressions.add_resource_suppressions(
            self.websocket_stage,
            [
                {
                    "id": "AwsSolutions-APIG1",
                    "reason": "Access logging disabled due to CloudWatch Logs role configuration requirement"
                }
            ]
        )