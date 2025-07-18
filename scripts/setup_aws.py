# File: scripts/setup_aws.py

import boto3
import os
import logging
import time
import subprocess
from botocore.exceptions import ProfileNotFound, NoCredentialsError, ClientError, ConfigParseError
from dotenv import load_dotenv
import sys
from datetime import datetime, timedelta

# Load environment variables from .env file if present
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

def check_aws_cli_availability():
    """Check if AWS CLI is available and working."""
    try:
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logging.info(f"AWS CLI found: {result.stdout.strip()}")
            return True
        else:
            logging.error("AWS CLI is installed but not working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        logging.error("AWS CLI is not installed or not accessible")
        return False

def get_aws_profile():
    """Get AWS profile from environment with improved fallback logic."""
    # Try multiple sources for AWS profile
    aws_profile = (
        os.environ.get('AWS_PROFILE') or 
        os.environ.get('AWS_DEFAULT_PROFILE') or
        'default'
    )
    
    logging.info(f"Using AWS profile: {aws_profile}")
    return aws_profile

def test_aws_credentials_via_cli(profile_name):
    """Test AWS credentials using AWS CLI directly."""
    try:
        cmd = ['aws', 'sts', 'get-caller-identity']
        if profile_name != 'default':
            cmd.extend(['--profile', profile_name])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            caller_info = json.loads(result.stdout)
            logging.info(f"AWS CLI authentication successful for profile '{profile_name}'")
            logging.info(f"Account: {caller_info.get('Account', 'Unknown')}")
            logging.info(f"User/Role: {caller_info.get('Arn', 'Unknown')}")
            return True
        else:
            logging.error(f"AWS CLI authentication failed: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("AWS CLI authentication timed out")
        return False
    except json.JSONDecodeError:
        logging.error("AWS CLI returned invalid JSON")
        return False
    except Exception as e:
        logging.error(f"Error testing AWS CLI credentials: {e}")
        return False

def setup_aws_credentials():
    """Set up AWS credentials using the specified profile with enhanced error handling."""
    
    # First check if AWS CLI is available
    if not check_aws_cli_availability():
        logging.error("AWS CLI is required but not available")
        provide_aws_installation_guidance()
        sys.exit(1)
    
    aws_profile = get_aws_profile()
    
    # Test credentials via AWS CLI first (more reliable)
    if not test_aws_credentials_via_cli(aws_profile):
        provide_aws_configuration_guidance(aws_profile)
        sys.exit(1)
    
    # Now try to create boto3 session
    try:
        if aws_profile == 'default':
            # For default profile, try without explicit profile first
            session = boto3.Session()
        else:
            session = boto3.Session(profile_name=aws_profile)
        
        # Test the session by making a simple API call
        sts = session.client('sts')
        caller_identity = sts.get_caller_identity()
        
        logging.info(f"Successfully authenticated using AWS profile: {aws_profile}")
        logging.info(f"Account ID: {caller_identity.get('Account', 'Unknown')}")
        logging.info(f"User ARN: {caller_identity.get('Arn', 'Unknown')}")
        
        return session
        
    except ProfileNotFound as e:
        logging.error(f"AWS profile '{aws_profile}' not found: {e}")
        provide_aws_configuration_guidance(aws_profile)
        sys.exit(1)
        
    except NoCredentialsError as e:
        logging.error(f"No AWS credentials found: {e}")
        provide_aws_configuration_guidance(aws_profile)
        sys.exit(1)
        
    except ConfigParseError as e:
        logging.error(f"AWS configuration file parsing error: {e}")
        provide_aws_configuration_guidance(aws_profile)
        sys.exit(1)
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'InvalidUserID.NotFound':
            logging.error("AWS credentials are invalid or expired")
        elif error_code == 'AccessDenied':
            logging.error("AWS credentials don't have sufficient permissions")
        else:
            logging.error(f"AWS API error: {e}")
        provide_aws_configuration_guidance(aws_profile)
        sys.exit(1)
        
    except Exception as e:
        logging.error(f"Unexpected error during AWS authentication: {e}")
        provide_aws_configuration_guidance(aws_profile)
        sys.exit(1)

def provide_aws_installation_guidance():
    """Provide guidance for installing AWS CLI."""
    logging.error("AWS CLI Installation Required:")
    logging.error("The AWS CLI is required but not found. Please install it:")
    logging.error("")
    logging.error("Option 1 - Automatic installation:")
    logging.error("  Run: python scripts/install_requirements.py")
    logging.error("")
    logging.error("Option 2 - Manual installation:")
    logging.error("  macOS: Download from https://awscli.amazonaws.com/AWSCLIV2.pkg")
    logging.error("  Linux: curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip")
    logging.error("  Windows: Download from https://awscli.amazonaws.com/AWSCLIV2.msi")
    logging.error("")
    logging.error("Option 3 - Package managers:")
    logging.error("  macOS: brew install awscli")
    logging.error("  Ubuntu/Debian: sudo apt install awscli")

def provide_aws_configuration_guidance(profile_name):
    """Provide comprehensive guidance for AWS configuration."""
    logging.error("AWS Configuration Required:")
    logging.error(f"Profile '{profile_name}' is not properly configured or accessible.")
    logging.error("")
    logging.error("SOLUTION OPTIONS:")
    logging.error("")
    logging.error("1. Configure AWS CLI (Recommended):")
    if profile_name == 'default':
        logging.error("   aws configure")
    else:
        logging.error(f"   aws configure --profile {profile_name}")
    logging.error("   (You'll be prompted for Access Key ID, Secret Access Key, and Region)")
    logging.error("")
    logging.error("2. Use Environment Variables:")
    logging.error("   export AWS_ACCESS_KEY_ID=your_access_key_here")
    logging.error("   export AWS_SECRET_ACCESS_KEY=your_secret_key_here")
    logging.error("   export AWS_DEFAULT_REGION=us-east-1")
    if profile_name != 'default':
        logging.error(f"   export AWS_PROFILE={profile_name}")
    logging.error("")
    logging.error("3. Use AWS SSO (if your organization uses it):")
    if profile_name == 'default':
        logging.error("   aws configure sso")
    else:
        logging.error(f"   aws configure sso --profile {profile_name}")
    logging.error("")
    logging.error("4. Use AWS Instance Profile (if running on EC2):")
    logging.error("   No configuration needed - uses EC2 instance role")
    logging.error("")
    logging.error("VERIFICATION:")
    logging.error("After configuration, test with:")
    if profile_name == 'default':
        logging.error("   aws sts get-caller-identity")
    else:
        logging.error(f"   aws sts get-caller-identity --profile {profile_name}")
    logging.error("")
    logging.error("CURRENT STATUS:")
    logging.error(f"   AWS_PROFILE: {os.environ.get('AWS_PROFILE', 'Not set')}")
    logging.error(f"   AWS_DEFAULT_PROFILE: {os.environ.get('AWS_DEFAULT_PROFILE', 'Not set')}")
    logging.error(f"   AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION', 'Not set')}")
    
    # Try to provide more specific guidance
    config_file = os.path.expanduser('~/.aws/config')
    credentials_file = os.path.expanduser('~/.aws/credentials')
    
    if not os.path.exists(config_file) and not os.path.exists(credentials_file):
        logging.error("")
        logging.error("NOTE: No AWS configuration files found.")
        logging.error("Start with 'aws configure' to create them.")
    elif os.path.exists(credentials_file):
        try:
            with open(credentials_file, 'r') as f:
                content = f.read()
                if f'[{profile_name}]' not in content and profile_name != 'default':
                    logging.error(f"")
                    logging.error(f"NOTE: Profile '[{profile_name}]' not found in {credentials_file}")
                    logging.error(f"Either use 'default' profile or create the '{profile_name}' profile.")
        except Exception:
            pass

def get_registered_nameservers(domain_name, session):
    """Get the registered nameservers for a domain."""
    client = session.client('route53domains')
    try:
        response = client.get_domain_detail(DomainName=domain_name)
        return sorted([ns['Name'] for ns in response['Nameservers']])
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'InvalidInput':
            logging.error(f"Domain {domain_name} is not valid or not found in Route53 Domains")
        elif error_code == 'UnsupportedTLD':
            logging.error(f"Domain {domain_name} has an unsupported TLD")
        else:
            logging.error(f"Error getting registered nameservers: {e}")
        return []

def get_hosted_zone_nameservers(hosted_zone_id, session):
    """Get the nameservers for a hosted zone."""
    client = session.client('route53')
    try:
        response = client.get_hosted_zone(Id=hosted_zone_id)
        return sorted(response['DelegationSet']['NameServers'])
    except ClientError as e:
        logging.error(f"Error getting hosted zone nameservers: {e}")
        return []

def update_registered_nameservers(domain_name, nameservers, session):
    """Update the registered nameservers for a domain."""
    client = session.client('route53domains')
    try:
        response = client.update_domain_nameservers(
            DomainName=domain_name,
            Nameservers=[{'Name': ns} for ns in nameservers]
        )
        operation_id = response['OperationId']
        logging.info(f"Nameserver update initiated. Operation ID: {operation_id}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'DuplicateRequest':
            logging.warning("Nameserver update already in progress")
            return True
        elif error_code == 'InvalidInput':
            logging.error(f"Invalid nameservers provided: {nameservers}")
        elif error_code == 'OperationLimitExceeded':
            logging.error("Too many operations in progress. Please wait and try again.")
        else:
            logging.error(f"Error updating nameservers: {e}")
        return False

def check_pending_operations(domain_name, session):
    """Check and wait for pending operations on a domain."""
    client = session.client('route53domains')
    try:
        response = client.list_operations(
            SubmittedSince=datetime.now() - timedelta(days=30)
        )
        pending_ops = [op['OperationId'] for op in response['Operations'] 
                      if op['Status'] == 'IN_PROGRESS' and op.get('DomainName') == domain_name]
        
        if pending_ops:
            logging.info(f"Pending operations found for {domain_name}. Waiting for completion...")
            waiter = client.get_waiter('operation_successful')
            for op_id in pending_ops:
                try:
                    waiter.wait(OperationId=op_id, WaiterConfig={'Delay': 30, 'MaxAttempts': 20})
                except Exception as e:
                    logging.warning(f"Error waiting for operation {op_id}: {e}")
            logging.info("Pending operations completed.")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'AccessDenied':
            logging.warning("Cannot check pending operations - insufficient permissions")
        else:
            logging.error(f"Error checking pending operations: {e}")

def create_or_get_hosted_zone(session, domain_name):
    """Create or get the Route53 hosted zone for the domain and sync nameservers."""
    client = session.client('route53')
    
    try:
        # Check if the hosted zone already exists
        hosted_zones = client.list_hosted_zones_by_name(DNSName=domain_name)['HostedZones']
        for zone in hosted_zones:
            if zone['Name'] == domain_name + '.':
                hosted_zone_id = zone['Id'].split('/')[-1]
                logging.info(f"Found existing hosted zone for {domain_name}")
                break
        else:
            # If not, create a new hosted zone
            response = client.create_hosted_zone(
                Name=domain_name, 
                CallerReference=str(hash(domain_name + str(time.time())))
            )
            hosted_zone_id = response['HostedZone']['Id'].split('/')[-1]
            logging.info(f"Created new hosted zone for {domain_name}")

        # Compare and update nameservers if necessary
        try:
            registered_ns = get_registered_nameservers(domain_name, session)
            hosted_zone_ns = get_hosted_zone_nameservers(hosted_zone_id, session)

            if registered_ns and hosted_zone_ns:
                if set(registered_ns) != set(hosted_zone_ns):
                    logging.info("Nameservers mismatch detected. Updating registered nameservers...")
                    if update_registered_nameservers(domain_name, hosted_zone_ns, session):
                        logging.info("Nameservers updated successfully.")
                    else:
                        logging.warning("Failed to update nameservers. Manual intervention may be required.")
                else:
                    logging.info("Nameservers are already in sync.")
            else:
                logging.warning("Could not compare nameservers - some may not be accessible")
        except Exception as e:
            logging.warning(f"Could not sync nameservers: {e}")
            logging.info("Hosted zone created successfully, but nameserver sync failed")

        return hosted_zone_id
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'HostedZoneAlreadyExists':
            logging.info("Hosted zone already exists, retrieving details...")
            # Try to find the existing zone
            try:
                zones = client.list_hosted_zones_by_name(DNSName=domain_name)['HostedZones']
                for zone in zones:
                    if zone['Name'] == domain_name + '.':
                        return zone['Id'].split('/')[-1]
            except Exception:
                pass
            raise
        elif error_code == 'AccessDenied':
            logging.error("Access denied when working with Route53. Check your permissions.")
        elif error_code == 'InvalidDomainName':
            logging.error(f"Invalid domain name: {domain_name}")
        else:
            logging.error(f"Error working with Route53: {e}")
        raise

def setup_aws(domain_name):
    """Set up AWS configuration and hosted zone."""
    logging.info(f"Setting up AWS for domain: {domain_name}")
    
    session = setup_aws_credentials()
    hosted_zone_id = create_or_get_hosted_zone(session, domain_name)
    
    logging.info(f"AWS setup completed. Hosted Zone ID: {hosted_zone_id}")
    return hosted_zone_id

if __name__ == '__main__':
    domain_name = os.getenv('DOMAIN_NAME')
    if not domain_name:
        raise ValueError("DOMAIN_NAME environment variable is not set.")
    setup_aws(domain_name)
