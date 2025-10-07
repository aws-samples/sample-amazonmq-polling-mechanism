from aws_cdk import Stack, CfnOutput, CfnParameter, Fn
from constructs import Construct
from modules.messaging import Messaging

class MessagingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Add dependency on VPC stack
        self.add_dependency(vpc_stack)
        
        self.messaging = Messaging(self, "Messaging", vpc=vpc_stack.vpc)
        
        CfnOutput(self, "MqBrokerId", value=self.messaging.mq_broker.ref)
        # Extract hostname from amqp+ssl://hostname:port format
        amqp_endpoint = Fn.select(0, self.messaging.mq_broker.attr_amqp_endpoints)
        # Use Fn.select to extract parts after splitting by '://'
        hostname_with_port = Fn.select(1, Fn.split("://", amqp_endpoint))
        # Extract just hostname (remove :5671 port)
        hostname = Fn.select(0, Fn.split(":", hostname_with_port))
        
        CfnOutput(self, "MqBrokerEndpoint", 
            value=Fn.sub(
                "ssl://${hostname}:61617",
                {"hostname": hostname}
            )
        )