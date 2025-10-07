from aws_cdk import (
    aws_cognito as cognito,
    aws_iam as iam
)
from constructs import Construct
from cdk_nag import NagSuppressions

class Auth(Construct):
    def __init__(self, scope: Construct, construct_id: str, table_arn: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Cognito Identity Pool - enable unauthenticated access
        self.identity_pool = cognito.CfnIdentityPool(self, "SpaIdentityPool",
            allow_unauthenticated_identities=True
        )

        # CDK-nag suppression for unauthenticated access
        NagSuppressions.add_resource_suppressions(
            self.identity_pool,
            [
                {
                    "id": "AwsSolutions-COG7",
                    "reason": "Demo application requires unauthenticated access for simplified user experience"
                }
            ]
        )

        # IAM role for unauthenticated users
        self.unauth_role = iam.Role(self, "UnauthRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "unauthenticated"
                    }
                },
                "sts:AssumeRoleWithWebIdentity"
            )
        )

        # Add DynamoDB permissions
        self.unauth_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:Scan", "dynamodb:PutItem", "dynamodb:UpdateItem"],
                resources=[table_arn]
            )
        )

        # Attach role to identity pool
        cognito.CfnIdentityPoolRoleAttachment(self, "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={
                "unauthenticated": self.unauth_role.role_arn
            }
        )