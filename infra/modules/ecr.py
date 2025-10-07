from aws_cdk import (
    aws_ecr as ecr,
    RemovalPolicy
)
from constructs import Construct

class ECR(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR Repository for Spring Boot
        self.repository = ecr.Repository(self, "SpringBootRepository",
            repository_name="reactive-spring-app",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10
                )
            ],
            removal_policy=RemovalPolicy.DESTROY
        )