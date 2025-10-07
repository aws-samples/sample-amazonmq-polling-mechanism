#!/bin/bash
set -e

# Load configuration
source ./config.sh

echo "🗑️  Destroying Reactive DynamoDB Demo..."

cd infra
source .venv/bin/activate 2>/dev/null || echo "Virtual environment not found, continuing..."

# Get all deployed stacks dynamically
echo "📋 Finding deployed stacks..."
DEPLOYED_STACKS=$(cdk list --app "$CDK_APP" 2>/dev/null || echo "")

if [ -z "$DEPLOYED_STACKS" ]; then
    echo "❌ No stacks found or CDK app failed to load"
    exit 1
fi

echo "📝 Found stacks: $DEPLOYED_STACKS"

# Destroy stacks in reverse dependency order
for stack in $DESTROY_ORDER; do

    if echo "$DEPLOYED_STACKS" | grep -q "$stack"; then
        # Special handling for ECRStack - delete repository images first
        if [ "$stack" = "ECRStack" ]; then
            echo "🧹 Cleaning ECR repository images..."
            aws ecr delete-repository --repository-name $REPO_NAME --force --region $AWS_REGION 2>/dev/null || echo "⚠️  ECR repository not found or already empty"
        fi
        
        # Special handling for FrontendStack - empty S3 bucket and clean global resources
        if [ "$stack" = "FrontendStack" ]; then
            echo "🧹 Emptying S3 bucket before stack deletion..."
            
            # Get all S3 buckets from the FrontendStack
            BUCKET_NAMES=$(aws cloudformation describe-stack-resources --stack-name FrontendStack --query 'StackResources[?ResourceType==`AWS::S3::Bucket`].PhysicalResourceId' --output text 2>/dev/null || echo "")
            
            if [ -n "$BUCKET_NAMES" ] && [ "$BUCKET_NAMES" != "None" ]; then
                for BUCKET_NAME in $BUCKET_NAMES; do
                    echo "📦 Found S3 bucket: $BUCKET_NAME"
                    echo "🗑️  Clearing all objects and versions from bucket..."
                    
                    # Delete all object versions and delete markers
                    aws s3api delete-objects --bucket "$BUCKET_NAME" --delete "$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || echo '{\"Objects\":[]}')" 2>/dev/null || true
                    aws s3api delete-objects --bucket "$BUCKET_NAME" --delete "$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || echo '{\"Objects\":[]}')" 2>/dev/null || true
                    
                    # Fallback: use s3 rm for any remaining objects
                    aws s3 rm s3://$BUCKET_NAME --recursive 2>/dev/null || true
                    
                    echo "✅ S3 bucket $BUCKET_NAME cleared"
                done
            fi
            
            # Clean up global CloudFront and WAF resources that might conflict
            echo "🧹 Cleaning up global CloudFront/WAF resources..."
            
            # Delete CloudFront Origin Access Controls with our naming pattern
            aws cloudfront list-origin-access-controls --query 'OriginAccessControlList.Items[?starts_with(Name, `spa-oac`)].Id' --output text 2>/dev/null | while read -r OAC_ID; do
                if [ -n "$OAC_ID" ] && [ "$OAC_ID" != "None" ]; then
                    echo "🗑️  Deleting CloudFront OAC: $OAC_ID"
                    aws cloudfront delete-origin-access-control --id "$OAC_ID" 2>/dev/null || echo "⚠️  Could not delete OAC $OAC_ID"
                fi
            done
            
            # Clean up WAF Web ACLs in us-east-1 (global CloudFront scope)
            ORIGINAL_REGION=$AWS_REGION
            export AWS_REGION=us-east-1
            aws wafv2 list-web-acls --scope CLOUDFRONT --query 'WebACLs[?starts_with(Name, `spa-web-acl`)].{Name:Name,Id:Id}' --output text 2>/dev/null | while read -r NAME ID; do
                if [ -n "$ID" ] && [ "$ID" != "None" ]; then
                    echo "🗑️  Deleting WAF WebACL: $NAME ($ID)"
                    aws wafv2 delete-web-acl --scope CLOUDFRONT --id "$ID" --lock-token "$(aws wafv2 get-web-acl --scope CLOUDFRONT --id "$ID" --query 'LockToken' --output text 2>/dev/null)" 2>/dev/null || echo "⚠️  Could not delete WebACL $ID"
                fi
            done
            export AWS_REGION=$ORIGINAL_REGION
        fi
        
        echo "🗑️  Destroying $stack..."
        cdk destroy $stack --app "$CDK_APP" --force
        echo "✅ $stack destroyed"
    else
        echo "⏭️  $stack not found, skipping..."
    fi
done

# Clean up output files
echo "🧹 Cleaning up output files..."
rm -f *-outputs.json outputs.json

echo "🎉 All stacks destroyed successfully!"
echo "💡 Note: S3 buckets and ECR repositories may need manual cleanup if they contain data"