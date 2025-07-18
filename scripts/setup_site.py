# File: scripts/setup_site.py

import os
import subprocess
import logging
import shutil
from scripts.customize_site import customize_site

# Set up logging
logging.basicConfig(level=logging.INFO)

def check_node_requirements():
    """Check if Node.js and npm meet minimum requirements."""
    node_cmd = shutil.which('node')
    npm_cmd = shutil.which('npm')
    
    if not node_cmd or not npm_cmd:
        raise RuntimeError(
            "Node.js and npm are required but not found. "
            "Please run 'python scripts/install_requirements.py' first."
        )
    
    try:
        # Check Node.js version
        result = subprocess.run([node_cmd, '--version'], capture_output=True, text=True, check=True)
        node_version = result.stdout.strip()
        
        # Extract major version number
        major_version = int(node_version.lstrip('v').split('.')[0])
        if major_version < 18:
            raise ValueError(f"Node.js version {node_version} is too old. Minimum required: v18.0.0")
        
        logging.info(f"Using Node.js {node_version}")
        
        # Check npm version
        result = subprocess.run([npm_cmd, '--version'], capture_output=True, text=True, check=True)
        npm_version = result.stdout.strip()
        logging.info(f"Using npm {npm_version}")
        
        return node_cmd, npm_cmd
        
    except (subprocess.CalledProcessError, ValueError, IndexError) as e:
        raise RuntimeError(f"Node.js version check failed: {e}")

def run_node_command(cmd, cwd=None, check=True):
    """Run a Node.js command with proper environment setup."""
    try:
        logging.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=False)
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd)}")
        raise

def setup_nextjs_app(domain_name):
    """Set up the Next.js application."""
    # Check Node.js requirements before proceeding
    node_cmd, npm_cmd = check_node_requirements()
    
    app_dir = 'next-app'
    if os.path.exists(app_dir):
        logging.info("Next.js app already exists. Skipping creation.")
    else:
        logging.info("Creating Next.js app...")
        # Use npx to create Next.js app with latest stable version
        create_cmd = [
            'npx', '--yes', 'create-next-app@latest', 'next-app',
            '--typescript', '--tailwind', '--eslint', '--app', 
            '--src-dir', '--import-alias', '@/*', '--use-npm', '--yes'
        ]
        run_node_command(create_cmd)
        
        # Add Next.js app to git
        logging.info("Adding Next.js app to git...")
        subprocess.run(['git', 'add', 'next-app'], check=True)
        subprocess.run(['git', 'commit', '-m', 'initial next.js app setup'], check=True)
        subprocess.run(['git', 'push'], check=True)
    
    # Install dependencies
    logging.info("Installing Node.js dependencies...")
    run_node_command([npm_cmd, 'install'], cwd=app_dir)

def build_nextjs_app():
    """Build the Next.js app."""
    logging.info("Building Next.js app...")
    node_cmd, npm_cmd = check_node_requirements()
    
    app_dir = 'next-app'
    
    # Ensure dependencies are installed
    run_node_command([npm_cmd, 'install'], cwd=app_dir)
    
    # Build the app
    run_node_command([npm_cmd, 'run', 'build'], cwd=app_dir)
    
    logging.info("Next.js app built successfully.")

def setup_site(domain_name):
    """Set up or rebuild the website."""
    app_dir = 'next-app'
    
    # Check if Next.js app exists and is properly initialized
    if not os.path.exists(app_dir) or not os.path.exists(os.path.join(app_dir, 'package.json')):
        logging.info("Setting up new Next.js application...")
        setup_nextjs_app(domain_name)
        customize_site(domain_name)
    else:
        logging.info("Next.js app already exists, checking for changes...")
        # Always customize site to ensure latest changes are applied
        customize_site(domain_name)
    
    # Build the app regardless of whether it's new or existing
    build_nextjs_app()
    logging.info("Site setup/rebuild complete!")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python setup_site.py <domain_name>")
        sys.exit(1)
    setup_site(sys.argv[1])
