#!/usr/bin/env python3
"""Deploy the fraud detection API"""

import os
import subprocess
import sys

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = ['flask', 'flask-cors', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {missing_packages}")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages, check=True)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            return False
    
    return True

def check_data_files():
    """Check if required data files exist"""
    print("\n📁 Checking data files...")
    
    required_files = [
        'data/currencies.json',
        'data/merchants.json', 
        'data/locations.json',
        'data/categories.json',
        'data/users.csv'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"\n⚠️ Missing data files: {missing_files}")
        print("Run the data creation scripts first!")
        return False
    
    return True

def start_api():
    """Start the fraud detection API"""
    print("\n🚀 Starting Fraud Detection API...")
    print("=" * 40)
    
    try:
        # Run the API
        subprocess.run([sys.executable, 'standalone_fraud_api.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 API stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ API failed to start: {e}")

def main():
    """Main deployment function"""
    print("🏦 Fraud Detection API Deployment")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed")
        return
    
    # Check data files
    if not check_data_files():
        print("❌ Data file check failed")
        return
    
    print("\n✅ All checks passed!")
    print("\n🎯 Deployment Options:")
    print("1. Start API locally (development)")
    print("2. Generate Docker deployment")
    print("3. Generate production config")
    print("4. Run API tests")
    
    choice = input("\nChoose option (1-4): ").strip()
    
    if choice == "1":
        start_api()
    elif choice == "2":
        generate_docker()
    elif choice == "3":
        generate_production_config()
    elif choice == "4":
        run_tests()
    else:
        print("Invalid choice")

def generate_docker():
    """Generate Docker deployment files"""
    print("\n🐳 Generating Docker deployment...")
    
    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "standalone_fraud_api.py"]
"""
    
    requirements_content = """flask==2.3.3
flask-cors==4.0.0
requests==2.31.0
faker==19.6.2
"""
    
    docker_compose_content = """version: '3.8'

services:
  fraud-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./data:/app/data
    restart: unless-stopped
"""
    
    # Write files
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile_content)
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements_content)
    
    with open('docker-compose.yml', 'w') as f:
        f.write(docker_compose_content)
    
    print("✅ Docker files generated:")
    print("  - Dockerfile")
    print("  - requirements.txt") 
    print("  - docker-compose.yml")
    print("\n🚀 To deploy with Docker:")
    print("  docker-compose up -d")

def generate_production_config():
    """Generate production configuration"""
    print("\n⚙️ Generating production configuration...")
    
    nginx_config = """server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
"""
    
    systemd_service = """[Unit]
Description=Fraud Detection API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/fraud-api
ExecStart=/opt/fraud-api/venv/bin/python standalone_fraud_api.py
Restart=always

[Install]
WantedBy=multi-user.target
"""
    
    with open('nginx.conf', 'w') as f:
        f.write(nginx_config)
    
    with open('fraud-api.service', 'w') as f:
        f.write(systemd_service)
    
    print("✅ Production files generated:")
    print("  - nginx.conf (Nginx reverse proxy)")
    print("  - fraud-api.service (systemd service)")

def run_tests():
    """Run API tests"""
    print("\n🧪 Running API tests...")
    
    try:
        subprocess.run([sys.executable, 'test_api.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")

if __name__ == "__main__":
    main()