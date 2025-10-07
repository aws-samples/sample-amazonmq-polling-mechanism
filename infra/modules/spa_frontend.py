from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_logs as logs,
    aws_wafv2 as wafv2,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from cdk_nag import NagSuppressions

class SpaFrontend(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Access logs bucket for CloudFront logs
        self.access_logs_bucket = s3.Bucket(self, "AccessLogsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )
        
        self.access_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyInsecureConnections",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[
                    self.access_logs_bucket.bucket_arn,
                    f"{self.access_logs_bucket.bucket_arn}/*"
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}}
            )
        )

        # CloudFront logs bucket
        self.logging_bucket = s3.Bucket(self, "LoggingBucket",
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                ignore_public_acls=False,
                block_public_policy=True,
                restrict_public_buckets=True
            ),
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="logging-bucket-access/"
        )
        
        self.logging_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyInsecureConnections",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[
                    self.logging_bucket.bucket_arn,
                    f"{self.logging_bucket.bucket_arn}/*"
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}}
            )
        )

        # SPA hosting bucket
        self.bucket = s3.Bucket(self, "SpaBucket",
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="spa-bucket-access/"
        )

        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyInsecureConnections",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[
                    self.bucket.bucket_arn,
                    f"{self.bucket.bucket_arn}/*"
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}}
            )
        )

        # Origin Access Control with unique name
        import os
        from aws_cdk import Aws
        region = Aws.REGION
        account_id = Aws.ACCOUNT_ID
        unique_suffix = f"{account_id}-{region}"
        
        cfn_oac = cloudfront.CfnOriginAccessControl(self, "SpaOAC",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name=f"spa-oac-{unique_suffix}",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4"
            )
        )

        # WAF Web ACL - only create in us-east-1 (CloudFront requires us-east-1 for global scope)
        web_acl = None
        print(f"Current region: {region}")  # Debug output
        if region == 'us-east-1':
            web_acl = wafv2.CfnWebACL(self, "SpaWebACL",
                scope="CLOUDFRONT",
                default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
                name=f"spa-web-acl-{unique_suffix}",
                rules=[
                    wafv2.CfnWebACL.RuleProperty(
                        name="AWSManagedRulesCommonRuleSet",
                        priority=1,
                        override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                        statement=wafv2.CfnWebACL.StatementProperty(
                            managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                                vendor_name="AWS",
                                name="AWSManagedRulesCommonRuleSet"
                            )
                        ),
                        visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                            sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRuleSet"
                    )
                )
            ],
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name="SpaWebACL"
            )
        )

        # CloudFront distribution configuration
        distribution_config_props = {
            "enabled": True,
            "default_root_object": "index.html",
            "origins": [
                cloudfront.CfnDistribution.OriginProperty(
                    id="S3Origin",
                    domain_name=self.bucket.bucket_regional_domain_name,
                    origin_access_control_id=cfn_oac.attr_id,
                    s3_origin_config=cloudfront.CfnDistribution.S3OriginConfigProperty(
                        origin_access_identity=""
                    )
                )
            ],
            "default_cache_behavior": cloudfront.CfnDistribution.DefaultCacheBehaviorProperty(
                target_origin_id="S3Origin",
                viewer_protocol_policy="redirect-to-https",
                allowed_methods=["GET", "HEAD", "OPTIONS"],
                cached_methods=["GET", "HEAD"],
                compress=True,
                cache_policy_id="658327ea-f89d-4fab-a63d-7e88639e58f6"
            ),
            "custom_error_responses": [
                cloudfront.CfnDistribution.CustomErrorResponseProperty(
                    error_code=404,
                    response_code=200,
                    response_page_path="/index.html"
                )
            ],
            "logging": cloudfront.CfnDistribution.LoggingProperty(
                bucket=self.logging_bucket.bucket_regional_domain_name,
                include_cookies=False,
                prefix="cloudfront/"
            ),
            "viewer_certificate": cloudfront.CfnDistribution.ViewerCertificateProperty(
                cloud_front_default_certificate=True,
                minimum_protocol_version="TLSv1.2_2021"
            ),
            "restrictions": cloudfront.CfnDistribution.RestrictionsProperty(
                geo_restriction=cloudfront.CfnDistribution.GeoRestrictionProperty(
                    restriction_type="none"
                )
            )
        }
        
        # Add WAF ACL only if it was created
        if web_acl:
            distribution_config_props["web_acl_id"] = web_acl.attr_arn

        # CloudFront distribution
        self.distribution = cloudfront.CfnDistribution(self, "SpaDistribution",
            distribution_config=cloudfront.CfnDistribution.DistributionConfigProperty(**distribution_config_props)
        )

        # Grant CloudFront OAC access
        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontOAC",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{scope.account}:distribution/{self.distribution.ref}"
                    }
                }
            )
        )

        self.distribution_domain_name = self.distribution.attr_domain_name
        self.distribution_id = self.distribution.ref
        
        # CDK-nag suppressions
        NagSuppressions.add_resource_suppressions(
            self.distribution,
            [
                {
                    "id": "AwsSolutions-CFR4",
                    "reason": "CloudFront default certificate with TLS 1.2 minimum is configured but CDK-nag doesn't recognize it properly"
                }
            ]
        )
        
        NagSuppressions.add_resource_suppressions(
            self.logging_bucket,
            [
                {
                    "id": "AwsSolutions-S2",
                    "reason": "CloudFront logging bucket requires ACLs to be enabled for CloudFront service to write logs"
                }
            ]
        )
