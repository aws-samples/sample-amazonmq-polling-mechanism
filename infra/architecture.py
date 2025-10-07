from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.network import CloudFront, VPC
from diagrams.aws.database import Dynamodb
from diagrams.aws.compute import ECS, ElasticLoadBalancing
from diagrams.aws.integration import MQ
from diagrams.aws.security import Cognito, IAM
from diagrams.aws.management import Cloudformation
from diagrams.onprem.client import Users
from diagrams.programming.framework import React, Spring
from diagrams.programming.language import Java

with Diagram("Complete Reactive DynamoDB Architecture", show=False, filename="architecture", direction="TB"):
    users = Users("Users")
    
    with Cluster("Development"):
        cdk = Cloudformation("AWS CDK\nInfrastructure")
        react_dev = React("React App\nDevelopment")
        spring_dev = Spring("Spring Boot\nDevelopment")
    
    with Cluster("AWS Cloud"):
        # Frontend Infrastructure
        with Cluster("Frontend (Static Hosting)"):
            cloudfront = CloudFront("CloudFront\nCDN + OAI")
            s3 = S3("S3 Bucket\n(Private)")
            
        # Authentication
        with Cluster("Authentication"):
            cognito = Cognito("Cognito\nIdentity Pool")
            iam = IAM("IAM Role\nUnauthenticated")
            
        # Backend Infrastructure  
        with Cluster("Backend (Container)"):
            alb = ElasticLoadBalancing("Application\nLoad Balancer")
            ecs = ECS("ECS Fargate\nSpring Boot API")
            
        # Messaging Infrastructure
        with Cluster("Message Queue (VPC)"):
            vpc = VPC("VPC\n1 AZ")
            mq = MQ("Amazon MQ\nActiveMQ Broker")
            
        # Database
        with Cluster("Database"):
            dynamodb = Dynamodb("DynamoDB\nItems Table")
    
    # Development to AWS
    cdk >> Edge(label="Deploy\nInfrastructure") >> [cloudfront, s3, cognito, alb, ecs, mq, dynamodb]
    react_dev >> Edge(label="Build &\nUpload") >> s3
    spring_dev >> Edge(label="Container\nImage") >> ecs
    
    # User Interactions
    users >> Edge(label="1. HTTPS\nAccess") >> cloudfront
    cloudfront >> Edge(label="Serve\nStatic Files") >> s3
    
    # Authentication Flow
    s3 >> Edge(label="Get\nCredentials") >> cognito
    cognito >> Edge(label="Assume\nRole") >> iam
    
    # Data Flow - React to DynamoDB
    s3 >> Edge(label="2. Poll every 3s\n(AWS SDK)", style="dashed") >> dynamodb
    iam >> Edge(label="DynamoDB\nPermissions") >> dynamodb
    
    # API Flow - Users to Spring Boot
    users >> Edge(label="3. POST /api/items\n{delay: N}") >> alb >> ecs
    
    # Spring Boot Processing
    ecs >> Edge(label="4a. Save Item\n(delay field)") >> dynamodb
    ecs >> Edge(label="4b. Queue Message\n(scheduled)") >> mq
    
    # Message Processing
    mq >> Edge(label="5. Dequeue after\nN seconds", color="red") >> ecs
    ecs >> Edge(label="6. Update\nlastModified", color="red") >> dynamodb
    
    # Infrastructure Dependencies
    vpc >> Edge(style="dotted") >> mq
    
    # Real-time Updates
    dynamodb >> Edge(label="7. Changes visible\nin React (3s)", color="green", style="dashed") >> s3