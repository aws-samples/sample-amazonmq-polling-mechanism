from aws_cdk import (
    aws_apprunner as apprunner,
    aws_iam as iam,
    aws_ec2 as ec2
)
from constructs import Construct
from cdk_nag import NagSuppressions

class AppRunner(Construct):
    def __init__(self, scope: Construct, construct_id: str, table_name: str, mq_broker_id: str, mq_endpoint: str, mq_username_secret_name: str, mq_password_secret_name: str, vpc, mq_security_group, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Task Role for DynamoDB and Secrets Manager access
        self.task_role = iam.Role(self, "TaskRole",
            assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
            inline_policies={
                "DynamoDBAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                                "dynamodb:Scan"
                            ],
                            resources=[f"arn:aws:dynamodb:{scope.region}:{scope.account}:table/{table_name}"]
                        )
                    ]
                ),
                "SecretsManagerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{scope.region}:{scope.account}:secret:{mq_username_secret_name}*",
                                f"arn:aws:secretsmanager:{scope.region}:{scope.account}:secret:{mq_password_secret_name}*"
                            ]
                        )
                    ]
                )
            }
        )

        # Access Role for ECR
        self.access_role = iam.Role(self, "AccessRole",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            inline_policies={
                "ECRAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage"
                            ],
                            resources=[f"arn:aws:ecr:{scope.region}:{scope.account}:repository/reactive-spring-app"]
                        )
                    ]
                )
            }
        )

        NagSuppressions.add_resource_suppressions(
            self.task_role,
            [
                {
                    "id": "AwsSolutions-IAM5", 
                    "reason": "Secrets Manager requires wildcard for version suffix", 
                    "appliesTo": [
                        "Resource::*",
                        "Resource::arn:aws:secretsmanager:<AWS::Region>:<AWS::AccountId>:secret:*",
                        f"Resource::arn:aws:secretsmanager:<AWS::Region>:<AWS::AccountId>:secret:{mq_username_secret_name}*",
                        f"Resource::arn:aws:secretsmanager:<AWS::Region>:<AWS::AccountId>:secret:{mq_password_secret_name}*",
                        "Resource::arn:aws:secretsmanager:<AWS::Region>:<AWS::AccountId>:secret:{\"Fn::Select\":[0,{\"Fn::Split\":[\"-\",{\"Fn::Select\":[6,{\"Fn::Split\":[\":\",{\"Ref\":\"MessagingMqUsername4AF1A2B0\"}]}]}]}]}-{\"Fn::Select\":[1,{\"Fn::Split\":[\"-\",{\"Fn::Select\":[6,{\"Fn::Split\":[\":\",{\"Ref\":\"MessagingMqUsername4AF1A2B0\"}]}]}]}]}*",
                        "Resource::arn:aws:secretsmanager:<AWS::Region>:<AWS::AccountId>:secret:{\"Fn::Select\":[0,{\"Fn::Split\":[\"-\",{\"Fn::Select\":[6,{\"Fn::Split\":[\":\",{\"Ref\":\"MessagingMqPassword6B7C8717\"}]}]}]}]}-{\"Fn::Select\":[1,{\"Fn::Split\":[\"-\",{\"Fn::Select\":[6,{\"Fn::Split\":[\":\",{\"Ref\":\"MessagingMqPassword6B7C8717\"}]}]}]}]}*"
                    ]
                }
            ],
            apply_to_children=True
        )
        NagSuppressions.add_resource_suppressions(
            self.access_role,
            [{"id": "AwsSolutions-IAM5", "reason": "ECR GetAuthorizationToken requires wildcard resource", "appliesTo": ["Resource::*"]}],
            apply_to_children=True
        )

        # App Runner Service using CfnService
        account_id = scope.account
        region = scope.region
        image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/reactive-spring-app:latest"

        # Create authentication configuration for ECR access
        auth_config = apprunner.CfnService.AuthenticationConfigurationProperty(
            access_role_arn=self.access_role.role_arn
        )

        # Create observability configuration
        observability_config = apprunner.CfnObservabilityConfiguration(self, "ObservabilityConfig",
            observability_configuration_name="reactive-spring-observability",
            trace_configuration=apprunner.CfnObservabilityConfiguration.TraceConfigurationProperty(
                vendor="AWSXRAY"
            )
        )

        # VPC Connector for accessing Amazon MQ in VPC
        vpc_connector = apprunner.CfnVpcConnector(self, "VpcConnector",
            subnets=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids,
            security_groups=[mq_security_group.security_group_id],
            vpc_connector_name="reactive-spring-vpc-connector"
        )

        self.service = apprunner.CfnService(self, "SpringService",
            network_configuration=apprunner.CfnService.NetworkConfigurationProperty(
                egress_configuration=apprunner.CfnService.EgressConfigurationProperty(
                    egress_type="VPC",
                    vpc_connector_arn=vpc_connector.attr_vpc_connector_arn
                )
            ),
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier=image_uri,
                    image_configuration=apprunner.CfnService.ImageConfigurationProperty(
                        port="8080",
                        runtime_environment_variables=[
                            apprunner.CfnService.KeyValuePairProperty(
                                name="DYNAMODB_TABLE_NAME",
                                value=table_name
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="MQ_BROKER_URL",
                                value=f"ssl://{mq_endpoint}:61617"
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="AWS_REGION",
                                value=region
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="MQ_USERNAME_SECRET_NAME",
                                value=mq_username_secret_name
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="MQ_PASSWORD_SECRET_NAME",
                                value=mq_password_secret_name
                            )
                        ]
                    ),
                    image_repository_type="ECR"
                ),
                auto_deployments_enabled=True,
                authentication_configuration=auth_config
            ),
            instance_configuration=apprunner.CfnService.InstanceConfigurationProperty(
                cpu="1 vCPU",
                memory="2 GB",
                instance_role_arn=self.task_role.role_arn
            ),
            service_name="reactive-spring-app",
            health_check_configuration=apprunner.CfnService.HealthCheckConfigurationProperty(
                protocol="HTTP",
                path="/actuator/health",
                interval=20,
                timeout=5,
                healthy_threshold=1,
                unhealthy_threshold=3
            ),
            observability_configuration=apprunner.CfnService.ServiceObservabilityConfigurationProperty(
                observability_enabled=True,
                observability_configuration_arn=observability_config.attr_observability_configuration_arn
            )
        )

        # Service URL and ID
        self.service_url = f"https://{self.service.attr_service_url}"
        self.service_id = self.service.attr_service_id