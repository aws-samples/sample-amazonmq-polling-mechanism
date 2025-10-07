from aws_cdk import Stack, CfnOutput
from constructs import Construct
from modules.vpc import VPC

class VPCStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create shared VPC
        self.vpc_construct = VPC(self, "VPC")
        self.vpc = self.vpc_construct.vpc

        # Outputs
        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        CfnOutput(self, "PublicSubnetIds", value=",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]))
        CfnOutput(self, "PrivateSubnetIds", value=",".join([subnet.subnet_id for subnet in self.vpc.private_subnets]))
        CfnOutput(self, "AvailabilityZones", value=",".join(self.vpc.availability_zones))