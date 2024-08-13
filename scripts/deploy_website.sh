#!/usr/bin/env bash

set -euo pipefail

deploy_website() {
    aws s3 sync next-app/out "s3://${DOMAIN_NAME}" --delete || { echo "Failed to sync website to S3" >&2; exit 1; }

    local distribution_id=$(cd terraform && terraform output -raw cloudfront_distribution_id)
    aws cloudfront create-invalidation --distribution-id "${distribution_id}" --paths "/*" || echo "Warning: Failed to invalidate CloudFront cache" >&2
}

deploy_website
