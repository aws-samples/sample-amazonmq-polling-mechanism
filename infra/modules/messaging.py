from aws_cdk import (
    aws_ec2 as ec2,
    aws_amazonmq as mq,
    aws_secretsmanager as secretsmanager,
    SecretValue
)
from constructs import Construct
from cdk_nag import NagSuppressions

class Messaging(Construct):
    def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Use VPC directly from stack reference
        self.vpc = vpc
        self.public_subnet = vpc.public_subnets[0]

        # Create secrets for MQ credentials with fixed values
        self.mq_username = secretsmanager.Secret(self, "MqUsername",
            description="Amazon MQ Username",
            secret_string_value=SecretValue.unsafe_plain_text('{"username": "admin"}')
        )

        self.mq_password = secretsmanager.Secret(self, "MqPassword",
            description="Amazon MQ Password",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"password": ""}',
                generate_string_key="password",
                exclude_characters="[],:=",
                include_space=False,
                password_length=16
            )
        )

        NagSuppressions.add_resource_suppressions(
            self.mq_username,
            [{"id": "AwsSolutions-SMG4", "reason": "Demo environment - rotation requires Lambda function"}]
        )
        NagSuppressions.add_resource_suppressions(
            self.mq_password,
            [{"id": "AwsSolutions-SMG4", "reason": "Demo environment - rotation requires Lambda function"}]
        )

        # Security Group for Amazon MQ
        self.mq_security_group = ec2.SecurityGroup(self, "MqSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=True
        )
        # Restrict access to VPC CIDR only
        self.mq_security_group.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(61617)
        )
        
        # CDK-nag suppression for VPC CIDR validation
        NagSuppressions.add_resource_suppressions(
            self.mq_security_group,
            [
                {
                    "id": "CdkNagValidationFailure",
                    "reason": "VPC CIDR block is resolved at runtime using intrinsic function",
                    "appliesTo": ["AwsSolutions-EC23"]
                }
            ]
        )

        # Amazon MQ Broker with scheduler support
        self.mq_broker = mq.CfnBroker(self, "SpaMqBroker",
            broker_name="spa-broker",
            deployment_mode="SINGLE_INSTANCE",
            engine_type="ACTIVEMQ",
            engine_version="5.18",
            host_instance_type="mq.t3.micro",
            publicly_accessible=True,
            configuration=mq.CfnBroker.ConfigurationIdProperty(
                id=self.create_broker_configuration().ref,
                revision=1
            ),
            users=[
                mq.CfnBroker.UserProperty(
                    username="admin",
                    password=self.mq_password.secret_value_from_json("password").unsafe_unwrap()
                )
            ],
            subnet_ids=[self.public_subnet.subnet_id],
            security_groups=[self.mq_security_group.security_group_id]
        )
    
    def create_broker_configuration(self):
        import base64
        config_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<broker xmlns="http://activemq.apache.org/schema/core" schedulerSupport="true">
  <transportConnectors>
    <transportConnector name="openwire" uri="tcp://0.0.0.0:61616?maximumConnections=1000&amp;wireFormat.maxFrameSize=104857600"/>
  </transportConnectors>
</broker>"""
        
        config_data = base64.b64encode(config_xml.encode('utf-8')).decode('utf-8')
        
        return mq.CfnConfiguration(self, "BrokerConfig",
            engine_type="ACTIVEMQ",
            engine_version="5.18",
            name="spa-broker-config",
            data=config_data
        )