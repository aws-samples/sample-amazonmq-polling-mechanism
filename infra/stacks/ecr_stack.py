from aws_cdk import Stack, CfnOutput
from constructs import Construct
from modules.ecr import ECR

class ECRStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create ECR repository
        ecr = ECR(self, "ECR")

        # Outputs
        CfnOutput(self, "RepositoryUri", value=ecr.repository.repository_uri)
        CfnOutput(self, "RepositoryName", value=ecr.repository.repository_name)