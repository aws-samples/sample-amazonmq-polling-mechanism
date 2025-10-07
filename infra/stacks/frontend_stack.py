from aws_cdk import Stack, CfnOutput
from constructs import Construct
from modules.spa_frontend import SpaFrontend

class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        frontend = SpaFrontend(self, "Frontend")
        
        CfnOutput(self, "BucketName", value=frontend.bucket.bucket_name)
        CfnOutput(self, "DistributionDomainName", value=frontend.distribution.attr_domain_name)
        CfnOutput(self, "DistributionId", value=frontend.distribution.ref)