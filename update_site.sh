#!/bin/bash

set -e

# Set up logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Build the Next.js app
build_next_app() {
    log "Building Next.js app..."
    cd next-app
    npm run build
    cd ..
    log "Next.js app built successfully."
}

# Get Terraform outputs
get_terraform_outputs() {
    log "Retrieving Terraform outputs..."
    cd terraform
    S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
    CLOUDFRONT_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
    cd ..
    log "Retrieved S3 bucket name: $S3_BUCKET_NAME"
    log "Retrieved CloudFront distribution ID: $CLOUDFRONT_DISTRIBUTION_ID"
}

# Sync S3 bucket
sync_s3_bucket() {
    log "Syncing files to S3 bucket '$S3_BUCKET_NAME'..."
    aws s3 sync next-app/out "s3://$S3_BUCKET_NAME" --delete --cache-control "no-store,max-age=0"
    log "Files synced to S3 bucket '$S3_BUCKET_NAME'."
}

# Invalidate CloudFront distribution
invalidate_cloudfront() {
    log "Creating invalidation for CloudFront distribution '$CLOUDFRONT_DISTRIBUTION_ID'..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" --paths "/*" --query 'Invalidation.Id' --output text)
    log "Invalidation '$INVALIDATION_ID' created."
}

# Main function
update_site() {
    log "Starting website update process..."
    build_next_app
    get_terraform_outputs
    sync_s3_bucket
    invalidate_cloudfront
    log "Website updated successfully!"
}

# Run the script
update_site