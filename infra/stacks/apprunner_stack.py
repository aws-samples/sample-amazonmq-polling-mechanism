from aws_cdk import Stack, CfnOutput, Fn
from constructs import Construct
from modules.app_runner import AppRunner

class AppRunnerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, database_stack, messaging_stack, vpc_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add dependencies
        self.add_dependency(database_stack)
        self.add_dependency(messaging_stack)
        self.add_dependency(vpc_stack)

        # Extract hostname from AMQP endpoint for SSL connection
        amqp_endpoint = Fn.select(0, messaging_stack.messaging.mq_broker.attr_amqp_endpoints)
        hostname_with_port = Fn.select(1, Fn.split("://", amqp_endpoint))
        hostname = Fn.select(0, Fn.split(":", hostname_with_port))
        
        # Create App Runner service
        self.app_runner = AppRunner(self, "AppRunner", 
            table_name=database_stack.database.table.table_name,
            mq_broker_id=messaging_stack.messaging.mq_broker.ref,
            mq_endpoint=hostname,
            mq_username_secret_name=messaging_stack.messaging.mq_username.secret_name,
            mq_password_secret_name=messaging_stack.messaging.mq_password.secret_name,
            vpc=vpc_stack.vpc,
            mq_security_group=messaging_stack.messaging.mq_security_group
        )

        # Outputs
        CfnOutput(self, "ServiceUrl", value=self.app_runner.service_url)
        CfnOutput(self, "ServiceArn", value=self.app_runner.service.attr_service_arn)
        CfnOutput(self, "ServiceId", value=self.app_runner.service_id)