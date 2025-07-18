# File: scripts/install_requirements.py

import sys
import subprocess
import shutil
import logging
import platform
import os
import tempfile
import zipfile
import tarfile
import urllib.request
import json

# Set up logging
logging.basicConfig(level=logging.INFO)

def get_platform_info():
    """Get platform information for cross-platform compatibility."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Normalize architecture names
    if machine in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'arm64'
    elif machine in ['i386', 'i686', 'x86']:
        arch = '386'
    elif machine.startswith('arm'):
        arch = 'arm'
    else:
        arch = machine
    
    return system, arch

def install_python_packages():
    """Install required Python packages using pip."""
    required_packages = [
        'boto3>=1.35.84',  # Latest stable version with all features
        'botocore>=1.35.84',
        'requests>=2.32.3',
        'python-dotenv>=1.0.1'
    ]
    
    logging.info("Installing Python packages...")
    for package in required_packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install {package}: {e}")
            raise

def check_and_install_aws_cli():
    """Check if AWS CLI is installed; if not, install it with platform detection."""
    if shutil.which('aws'):
        logging.info("AWS CLI is already installed.")
        return
    
    logging.info("AWS CLI not found. Installing AWS CLI v2...")
    system, arch = get_platform_info()
    
    try:
        if system == 'darwin':  # macOS
            _install_aws_cli_macos()
        elif system == 'linux':
            _install_aws_cli_linux(arch)
        elif system == 'windows':
            _install_aws_cli_windows()
        else:
            raise ValueError(f"Unsupported platform: {system}")
            
        # Verify installation
        if not shutil.which('aws'):
            raise RuntimeError("AWS CLI installation failed - command not found after installation")
            
        logging.info("AWS CLI v2 installed successfully.")
        
    except Exception as e:
        logging.error(f"Failed to install AWS CLI: {e}")
        logging.error("Please install AWS CLI manually from https://aws.amazon.com/cli/")
        raise

def _install_aws_cli_macos():
    """Install AWS CLI on macOS."""
    url = "https://awscli.amazonaws.com/AWSCLIV2.pkg"
    with tempfile.NamedTemporaryFile(suffix='.pkg', delete=False) as tmp_file:
        urllib.request.urlretrieve(url, tmp_file.name)
        subprocess.check_call(['sudo', 'installer', '-pkg', tmp_file.name, '-target', '/'])
        os.unlink(tmp_file.name)

def _install_aws_cli_linux(arch):
    """Install AWS CLI on Linux with proper architecture detection."""
    if arch == 'amd64':
        url = "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"
    elif arch == 'arm64':
        url = "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"
    else:
        raise ValueError(f"Unsupported Linux architecture: {arch}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'awscliv2.zip')
        urllib.request.urlretrieve(url, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        install_script = os.path.join(temp_dir, 'aws', 'install')
        subprocess.check_call(['sudo', install_script])

def _install_aws_cli_windows():
    """Install AWS CLI on Windows."""
    url = "https://awscli.amazonaws.com/AWSCLIV2.msi"
    with tempfile.NamedTemporaryFile(suffix='.msi', delete=False) as tmp_file:
        urllib.request.urlretrieve(url, tmp_file.name)
        subprocess.check_call(['msiexec.exe', '/i', tmp_file.name, '/quiet'])
        os.unlink(tmp_file.name)

def get_latest_terraform_version():
    """Get the latest stable Terraform version from HashiCorp releases."""
    try:
        url = "https://api.releases.hashicorp.com/v1/releases/terraform?limit=20"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        
        # Find the latest non-prerelease version
        for release in data:
            version = release.get('version', '')
            if not any(keyword in version.lower() for keyword in ['alpha', 'beta', 'rc', 'pre']):
                return version
        
        # Fallback to known stable version
        return "1.12.2"
    except Exception as e:
        logging.warning(f"Could not fetch latest Terraform version: {e}")
        return "1.12.2"  # Fallback to known stable version

def check_and_install_terraform():
    """Check if Terraform is installed; if not, install it with platform detection."""
    if shutil.which('terraform'):
        logging.info("Terraform is already installed.")
        return
    
    logging.info("Terraform not found. Installing Terraform...")
    system, arch = get_platform_info()
    terraform_version = get_latest_terraform_version()
    
    try:
        if system == 'darwin':  # macOS
            _install_terraform_macos()
        elif system == 'linux':
            _install_terraform_linux(terraform_version, arch)
        elif system == 'windows':
            _install_terraform_windows(terraform_version, arch)
        else:
            raise ValueError(f"Unsupported platform: {system}")
            
        # Verify installation
        if not shutil.which('terraform'):
            raise RuntimeError("Terraform installation failed - command not found after installation")
            
        logging.info(f"Terraform {terraform_version} installed successfully.")
        
    except Exception as e:
        logging.error(f"Failed to install Terraform: {e}")
        logging.error("Please install Terraform manually from https://www.terraform.io/downloads")
        raise

def _install_terraform_macos():
    """Install Terraform on macOS using Homebrew."""
    if shutil.which('brew'):
        subprocess.check_call(['brew', 'tap', 'hashicorp/tap'])
        subprocess.check_call(['brew', 'install', 'hashicorp/tap/terraform'])
    else:
        # Manual installation for macOS without Homebrew
        system, arch = get_platform_info()
        terraform_version = get_latest_terraform_version()
        _install_terraform_binary('darwin', arch, terraform_version)

def _install_terraform_linux(terraform_version, arch):
    """Install Terraform on Linux."""
    _install_terraform_binary('linux', arch, terraform_version)

def _install_terraform_windows(terraform_version, arch):
    """Install Terraform on Windows."""
    _install_terraform_binary('windows', arch, terraform_version)

def _install_terraform_binary(system, arch, version):
    """Install Terraform binary for the given platform."""
    # Map our arch names to Terraform's naming convention
    tf_arch_map = {
        'amd64': 'amd64',
        'arm64': 'arm64',
        '386': '386',
        'arm': 'arm'
    }
    
    tf_arch = tf_arch_map.get(arch, arch)
    
    if system == 'windows':
        filename = f"terraform_{version}_{system}_{tf_arch}.zip"
        binary_name = 'terraform.exe'
        install_dir = '/usr/local/bin' if os.name != 'nt' else 'C:\\Windows\\System32'
    else:
        filename = f"terraform_{version}_{system}_{tf_arch}.zip"
        binary_name = 'terraform'
        install_dir = '/usr/local/bin'
    
    url = f"https://releases.hashicorp.com/terraform/{version}/{filename}"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, filename)
        urllib.request.urlretrieve(url, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        binary_path = os.path.join(temp_dir, binary_name)
        target_path = os.path.join(install_dir, binary_name)
        
        if system in ['darwin', 'linux']:
            subprocess.check_call(['sudo', 'mv', binary_path, target_path])
            subprocess.check_call(['sudo', 'chmod', '+x', target_path])
        else:  # Windows
            shutil.move(binary_path, target_path)

def get_latest_node_lts_version():
    """Get the latest LTS Node.js version from Node.js releases API."""
    try:
        url = "https://nodejs.org/dist/index.json"
        with urllib.request.urlopen(url, timeout=10) as response:
            releases = json.loads(response.read().decode('utf-8'))
        
        # Find the latest LTS version
        for release in releases:
            if release.get('lts'):
                version = release['version'].lstrip('v')
                logging.info(f"Latest Node.js LTS version: {version}")
                return version
                
        # Fallback to a known stable LTS version
        logging.warning("Could not determine latest LTS version, using fallback")
        return "20.18.1"
        
    except Exception as e:
        logging.warning(f"Could not fetch latest Node.js LTS version: {e}")
        return "20.18.1"

def check_and_install_node():
    """Check if Node.js and npm are installed; if not, install them with platform detection."""
    node_found = shutil.which('node')
    npm_found = shutil.which('npm')
    
    if node_found and npm_found:
        try:
            # Check Node.js version
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                current_version = result.stdout.strip().lstrip('v')
                logging.info(f"Node.js {current_version} and npm are already installed.")
                return
        except Exception:
            pass
        logging.info("Node.js and npm are already installed.")
        return
    
    system, machine, arch = get_platform_info()
    node_version = get_latest_node_lts_version()
    
    logging.warning("Node.js or npm not found.")
    logging.info(f"Installing Node.js v{node_version}...")
    
    if system == 'darwin':
        if shutil.which('brew'):
            logging.info("Installing Node.js via Homebrew...")
            try:
                subprocess.check_call(['brew', 'install', 'node'])
                logging.info("Node.js installed successfully via Homebrew.")
                return
            except subprocess.CalledProcessError:
                logging.warning("Homebrew installation failed, trying binary installation...")
                _install_node_binary('darwin', arch, node_version)
        else:
            _install_node_binary('darwin', arch, node_version)
    
    elif system == 'linux':
        # Try package manager first, then fallback to binary
        package_managers = [
            (['apt'], ["sudo", "apt", "update"], ["sudo", "apt", "install", "-y", "nodejs", "npm"]),
            (['yum'], [], ["sudo", "yum", "install", "-y", "nodejs", "npm"]),
            (['dnf'], [], ["sudo", "dnf", "install", "-y", "nodejs", "npm"]),
            (['pacman'], [], ["sudo", "pacman", "-S", "nodejs", "npm"])
        ]
        
        for pm_check, update_cmd, install_cmd in package_managers:
            if shutil.which(pm_check[0]):
                logging.info(f"Installing Node.js via package manager: {' '.join(install_cmd)}")
                try:
                    if update_cmd:
                        subprocess.check_call(update_cmd)
                    subprocess.check_call(install_cmd)
                    logging.info("Node.js installed successfully via package manager.")
                    return
                except subprocess.CalledProcessError:
                    logging.warning("Package manager installation failed, trying binary installation...")
                    break
        
        _install_node_binary('linux', arch, node_version)
        
    elif system == 'windows':
        _install_node_binary('windows', arch, node_version)
        
    else:
        logging.error("Unsupported platform for automatic Node.js installation")
        logging.error("Please install Node.js manually from https://nodejs.org/")
        raise RuntimeError("Node.js installation required but not found")
    
    # Verify installation
    if not shutil.which('node') or not shutil.which('npm'):
        raise RuntimeError("Node.js installation failed - commands not found after installation")
    
    logging.info(f"Node.js v{node_version} installed successfully.")

def _install_node_binary(system, arch, version):
    """Install Node.js binary for the given platform."""
    # Map our arch names to Node.js naming convention
    node_arch_map = {
        'amd64': 'x64',
        'arm64': 'arm64',
        '386': 'x86'
    }
    
    node_arch = node_arch_map.get(arch, arch)
    
    if system == 'windows':
        filename = f"node-v{version}-win-{node_arch}.zip"
        binary_name = 'node.exe'
    else:
        filename = f"node-v{version}-{system}-{node_arch}.tar.xz"
        binary_name = 'node'
    
    url = f"https://nodejs.org/dist/v{version}/{filename}"
    
    try:
        logging.info(f"Downloading Node.js from {url}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, filename)
            
            # Download the archive
            urllib.request.urlretrieve(url, archive_path)
            
            # Extract the archive
            extract_dir = os.path.join(temp_dir, 'node_extract')
            os.makedirs(extract_dir, exist_ok=True)
            
            if filename.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                with tarfile.open(archive_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # Find the extracted directory
            extracted_items = os.listdir(extract_dir)
            if not extracted_items:
                raise RuntimeError("No files extracted from Node.js archive")
            
            node_dir = os.path.join(extract_dir, extracted_items[0])
            
            # Install to appropriate location
            if system == 'windows':
                install_dir = os.path.expanduser('~/AppData/Local/nodejs')
            else:
                install_dir = '/usr/local'
                
            os.makedirs(install_dir, exist_ok=True)
            
            # Copy files
            if system == 'windows':
                # Copy all files to install directory
                import shutil as sh
                for item in os.listdir(node_dir):
                    src = os.path.join(node_dir, item)
                    dst = os.path.join(install_dir, item)
                    if os.path.isdir(src):
                        sh.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        sh.copy2(src, dst)
                
                # Add to PATH
                node_path = install_dir
                current_path = os.environ.get('PATH', '')
                if node_path not in current_path:
                    os.environ['PATH'] = f"{node_path};{current_path}"
            else:
                # Copy bin directory contents
                bin_src = os.path.join(node_dir, 'bin')
                bin_dst = os.path.join(install_dir, 'bin')
                
                if os.path.exists(bin_src):
                    os.makedirs(bin_dst, exist_ok=True)
                    for item in os.listdir(bin_src):
                        src_path = os.path.join(bin_src, item)
                        dst_path = os.path.join(bin_dst, item)
                        import shutil as sh
                        sh.copy2(src_path, dst_path)
                        os.chmod(dst_path, 0o755)
                
                # Copy lib directory if it exists
                lib_src = os.path.join(node_dir, 'lib')
                if os.path.exists(lib_src):
                    lib_dst = os.path.join(install_dir, 'lib')
                    import shutil as sh
                    sh.copytree(lib_src, lib_dst, dirs_exist_ok=True)
            
            logging.info(f"Node.js binary installed to {install_dir}")
            
    except Exception as e:
        logging.error(f"Failed to install Node.js binary: {e}")
        logging.error("Please install Node.js manually from https://nodejs.org/")
        raise RuntimeError("Node.js binary installation failed")

def verify_aws_cli_config():
    """Verify AWS CLI is properly configured and provide helpful guidance."""
    try:
        # Check if AWS CLI is available
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("AWS CLI not found in PATH")
        
        logging.info(f"AWS CLI version: {result.stdout.strip()}")
        
        # Check for basic configuration
        try:
            result = subprocess.run(['aws', 'configure', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("AWS CLI configuration found.")
                # Check if credentials are actually configured
                if 'access_key' in result.stdout.lower() or 'profile' in result.stdout.lower():
                    logging.info("AWS credentials appear to be configured.")
                else:
                    logging.warning("AWS CLI may not be fully configured.")
                    _provide_aws_config_guidance()
            else:
                logging.warning("AWS CLI configuration issues detected.")
                _provide_aws_config_guidance()
        except subprocess.CalledProcessError:
            logging.warning("Could not check AWS CLI configuration.")
            _provide_aws_config_guidance()
            
    except Exception as e:
        logging.error(f"AWS CLI verification failed: {e}")
        _provide_aws_config_guidance()

def _provide_aws_config_guidance():
    """Provide helpful guidance for AWS CLI configuration."""
    logging.info("AWS CLI Configuration Guidance:")
    logging.info("1. Run 'aws configure' to set up your default profile")
    logging.info("2. Or set environment variables:")
    logging.info("   export AWS_ACCESS_KEY_ID=your_access_key")
    logging.info("   export AWS_SECRET_ACCESS_KEY=your_secret_key")
    logging.info("   export AWS_DEFAULT_REGION=us-east-1")
    logging.info("3. Or use AWS SSO: aws configure sso")
    logging.info("4. Ensure your AWS_PROFILE environment variable is set if using named profiles")

def install_requirements():
    """Install all required tools and packages."""
    logging.info("Starting installation of requirements...")
    
    try:
        install_python_packages()
        check_and_install_aws_cli()
        verify_aws_cli_config()
        check_and_install_terraform()
        check_and_install_node()
        
        logging.info("All requirements installation completed successfully.")
        
    except Exception as e:
        logging.error(f"Installation failed: {e}")
        logging.error("Please resolve the issues above before proceeding.")
        raise

if __name__ == '__main__':
    install_requirements()
