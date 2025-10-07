# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-08

### Added
- Initial release of Priority-Based Message Processing Demo
- Complete serverless architecture with AWS CDK deployment
- Spring Boot backend on AWS App Runner with JMS priority processing
- React frontend with real-time WebSocket updates
- DynamoDB integration with Streams for real-time notifications
- Amazon MQ ActiveMQ broker with priority-based message queuing
- Application-level delay processing using CompletableFuture
- High priority message bypass for immediate processing
- Dual-layer retry mechanisms (Spring @Retryable + ActiveMQ RedeliveryPolicy)
- Dead Letter Queue support for permanent failures
- Real-time MQ monitoring panel with activity logs
- Complete CRUD operations for message management
- Dynamic configuration injection during deployment
- Comprehensive testing scripts for priority demonstration
- Architecture diagrams and documentation
- Blog post template and SIM ticket for AWS publication

### Features
- **Priority Levels**: High (9), Medium (4), Low (0) with JMS priority ordering
- **Real-time Updates**: Instant WebSocket notifications from DynamoDB Streams
- **Delay Processing**: Configurable delays with high priority bypass
- **Fault Tolerance**: Exponential backoff, message persistence, recovery methods
- **Monitoring**: Live queue statistics and activity tracking
- **Auto-scaling**: AWS App Runner with automatic scaling based on traffic
- **Security**: Cognito authentication with IAM role-based access
- **Infrastructure as Code**: Complete AWS CDK deployment with modular stacks

### Infrastructure
- Frontend: S3 + CloudFront with React SPA
- Backend: Spring Boot on AWS App Runner with ECR container registry
- Database: DynamoDB with Streams integration
- Messaging: Amazon MQ ActiveMQ with VPC isolation
- Authentication: Cognito Identity Pool with IAM roles
- Real-time: API Gateway WebSocket with Lambda processors
- Deployment: Single-command deployment with automatic configuration

### Documentation
- Comprehensive README with architecture overview
- API documentation with example requests
- Deployment guide with prerequisites
- Testing scripts with priority demonstrations
- Blog post template for technical publication
- Project governance files (LICENSE, CODE_OF_CONDUCT, CONTRIBUTING)

## [Unreleased]

### Planned
- Multi-region deployment support
- Enhanced monitoring with CloudWatch dashboards
- Performance optimization for high-throughput scenarios
- Additional message priority levels
- Batch processing capabilities