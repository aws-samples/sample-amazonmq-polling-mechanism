from aws_cdk import (
    aws_cloudwatch as cloudwatch,
    aws_logs as logs
)
from constructs import Construct

class Monitoring(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
                 app_runner_service_name: str,
                 app_runner_service_id: str,
                 mq_broker_name: str,
                 dynamodb_table_name: str,
                 lambda_function_name: str,
                 websocket_api_id: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Use the service ID passed from the stack
        service_id = app_runner_service_id
        
        # Main Application Dashboard
        self.main_dashboard = cloudwatch.Dashboard(
            self, "MainDashboard",
            dashboard_name="reactive-messaging-app"
        )
        
        # App Runner Metrics - Using correct dimensions
        self.main_dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="App Runner - CPU & Memory",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner",
                        metric_name="CPUUtilization",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner", 
                        metric_name="MemoryUtilization",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    )
                ],
                width=12
            ),
            
            cloudwatch.GraphWidget(
                title="App Runner - Requests & Response Times",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner",
                        metric_name="Requests",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner",
                        metric_name="2xxStatusResponses",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner",
                        metric_name="4xxStatusResponses",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner",
                        metric_name="RequestLatency",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    )
                ],
                width=12
            )
        )
        
        # Amazon MQ Metrics - Using correct broker name
        broker_name = "spa-broker-1"  # Actual broker name from metrics
        
        self.main_dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Amazon MQ - Queue Metrics",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="QueueSize",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        },
                        label="Main Queue Size"
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ", 
                        metric_name="QueueSize",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "ActiveMQ.DLQ"
                        },
                        label="Dead Letter Queue"
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="ConsumerCount",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="ProducerCount",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        }
                    )
                ],
                width=12
            ),
            
            cloudwatch.GraphWidget(
                title="Amazon MQ - Message Throughput",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="EnqueueCount",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        },
                        statistic="Sum"
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="DequeueCount", 
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        },
                        statistic="Sum"
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="DispatchCount",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        },
                        statistic="Sum"
                    )
                ],
                width=12
            )
        )
        
        # Broker Health Metrics
        self.main_dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Amazon MQ Broker - System Resources",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="CpuUtilization",
                        dimensions_map={"Broker": broker_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="HeapUsage",
                        dimensions_map={"Broker": broker_name}
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="StorePercentUsage",
                        dimensions_map={"Broker": broker_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="TempPercentUsage",
                        dimensions_map={"Broker": broker_name}
                    )
                ],
                width=12
            ),
            
            cloudwatch.GraphWidget(
                title="Amazon MQ - Connections & Network",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="CurrentConnectionsCount",
                        dimensions_map={"Broker": broker_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="TotalProducerCount",
                        dimensions_map={"Broker": broker_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="TotalConsumerCount",
                        dimensions_map={"Broker": broker_name}
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="NetworkIn",
                        dimensions_map={"Broker": broker_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="NetworkOut",
                        dimensions_map={"Broker": broker_name}
                    )
                ],
                width=12
            )
        )
        
        # DynamoDB Metrics
        self.main_dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="DynamoDB - Read/Write Operations",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedReadCapacityUnits",
                        dimensions_map={"TableName": dynamodb_table_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedWriteCapacityUnits",
                        dimensions_map={"TableName": dynamodb_table_name}
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="SuccessfulRequestLatency",
                        dimensions_map={
                            "TableName": dynamodb_table_name,
                            "Operation": "GetItem"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="SuccessfulRequestLatency",
                        dimensions_map={
                            "TableName": dynamodb_table_name,
                            "Operation": "PutItem"
                        }
                    )
                ],
                width=12
            ),
            
            cloudwatch.GraphWidget(
                title="DynamoDB - Errors & Throttles",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ReadThrottles",
                        dimensions_map={"TableName": dynamodb_table_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="WriteThrottles", 
                        dimensions_map={"TableName": dynamodb_table_name}
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="SystemErrors",
                        dimensions_map={"TableName": dynamodb_table_name}
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="UserErrors",
                        dimensions_map={"TableName": dynamodb_table_name}
                    )
                ],
                width=12
            )
        )
        
        # Lambda & WebSocket (if they exist)
        if lambda_function_name:
            self.main_dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title="Lambda Stream Processor",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Invocations",
                            dimensions_map={"FunctionName": lambda_function_name}
                        ),
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Errors",
                            dimensions_map={"FunctionName": lambda_function_name}
                        )
                    ],
                    right=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Duration",
                            dimensions_map={"FunctionName": lambda_function_name}
                        )
                    ],
                    width=12
                )
            )
        
        if websocket_api_id:
            self.main_dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title="WebSocket API",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/ApiGateway",
                            metric_name="Count",
                            dimensions_map={"ApiId": websocket_api_id}
                        ),
                        cloudwatch.Metric(
                            namespace="AWS/ApiGateway",
                            metric_name="4XXError",
                            dimensions_map={"ApiId": websocket_api_id}
                        )
                    ],
                    right=[
                        cloudwatch.Metric(
                            namespace="AWS/ApiGateway",
                            metric_name="IntegrationLatency",
                            dimensions_map={"ApiId": websocket_api_id}
                        )
                    ],
                    width=12
                )
            )
        
        # Summary Widgets
        self.main_dashboard.add_widgets(
            cloudwatch.SingleValueWidget(
                title="Active Instances",
                metrics=[
                    cloudwatch.Metric(
                        namespace="AWS/AppRunner",
                        metric_name="ActiveInstances",
                        dimensions_map={
                            "ServiceName": app_runner_service_name,
                            "ServiceID": service_id
                        }
                    )
                ],
                width=6
            ),
            
            cloudwatch.SingleValueWidget(
                title="Queue Messages",
                metrics=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="QueueSize",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "item.queue"
                        }
                    )
                ],
                width=6
            ),
            
            cloudwatch.SingleValueWidget(
                title="DLQ Messages",
                metrics=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="QueueSize",
                        dimensions_map={
                            "Broker": broker_name,
                            "Queue": "ActiveMQ.DLQ"
                        }
                    )
                ],
                width=6
            ),
            
            cloudwatch.SingleValueWidget(
                title="Total Messages",
                metrics=[
                    cloudwatch.Metric(
                        namespace="AWS/AmazonMQ",
                        metric_name="TotalMessageCount",
                        dimensions_map={"Broker": broker_name}
                    )
                ],
                width=6
            )
        )
