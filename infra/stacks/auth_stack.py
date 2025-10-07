from aws_cdk import Stack, CfnOutput, CfnParameter
from constructs import Construct
from modules.auth import Auth

class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        table_arn = CfnParameter(self, "TableArn", type="String")
        
        auth = Auth(self, "Auth", table_arn=table_arn.value_as_string)
        
        CfnOutput(self, "IdentityPoolId", value=auth.identity_pool.ref)