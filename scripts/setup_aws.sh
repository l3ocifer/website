#!/usr/bin/env bash

set -euo pipefail

setup_aws_credentials() {
    if [ -z "${AWS_PROFILE:-}" ]; then
        if [ -f .env ]; then
            source .env
        fi
        if [ -z "${AWS_PROFILE:-}" ]; then
            echo "WARNING: AWS_PROFILE is not set. Using default profile." >&2
            AWS_PROFILE=default
        fi
    fi
    export AWS_PROFILE

    if ! aws sts get-caller-identity &> /dev/null; then
        echo "AWS credentials not configured. Running 'aws configure'..." >&2
        aws configure || { echo "Failed to configure AWS credentials." >&2; exit 1; }
        echo "AWS_PROFILE=${AWS_PROFILE}" > .env
    fi
}

check_aws_cli_version() {
    local min_version="2.0.0"
    local current_version=$(aws --version 2>&1 | cut -d/ -f2 | cut -d' ' -f1)
    if [ "$(printf '%s\n' "$min_version" "$current_version" | sort -V | head -n1)" != "$min_version" ]; then
        echo "ERROR: AWS CLI version $current_version is less than the required version $min_version" >&2
        exit 1
    fi
}

create_or_get_hosted_zone() {
    DOMAIN_NAME=$(cat .domain)
    HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name --dns-name "${DOMAIN_NAME}." --query "HostedZones[?Name == '${DOMAIN_NAME}.'].Id" --output text)
    if [[ -z "$HOSTED_ZONE_ID" ]]; then
        echo "No hosted zone found for ${DOMAIN_NAME}. Creating a new one."
        HOSTED_ZONE_ID=$(aws route53 create-hosted-zone --name "${DOMAIN_NAME}" --caller-reference "$(date +%s)" --query "HostedZone.Id" --output text)
        echo "Created new hosted zone with ID: ${HOSTED_ZONE_ID}"
    else
        echo "Existing hosted zone found for ${DOMAIN_NAME} with ID: ${HOSTED_ZONE_ID}"
    fi
    HOSTED_ZONE_ID=$(echo "$HOSTED_ZONE_ID" | sed 's/^\/hostedzone\///')
    echo "${HOSTED_ZONE_ID}" > .hosted_zone_id
    echo "Hosted zone ID saved to .hosted_zone_id file"
}

check_acm_certificate() {
    DOMAIN_NAME=$(cat .domain)
    ACM_CERT_ARN=$(aws acm list-certificates --region us-east-1 --query "CertificateSummaryList[?DomainName=='$DOMAIN_NAME'].CertificateArn" --output text)
    if [ -n "$ACM_CERT_ARN" ]; then
        echo "ACM certificate for $DOMAIN_NAME already exists."
        echo "true" > .acm_cert_exists
    else
        echo "ACM certificate for $DOMAIN_NAME does not exist."
        echo "false" > .acm_cert_exists
    fi
}

# Main execution
check_aws_cli_version
setup_aws_credentials
create_or_get_hosted_zone
check_acm_certificate