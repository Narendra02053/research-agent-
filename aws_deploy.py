# aws_deploy.py - Script to deploy the application to AWS.
import os
import sys
import time
import subprocess

# Ensure required libraries are installed
try:
    import boto3
    import paramiko
except ImportError:
    print("Installing required dependencies: boto3, paramiko...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3", "paramiko", "python-dotenv"])
    import boto3
    import paramiko

from dotenv import load_dotenv

# Load AWS Credentials
env_path = os.path.join(os.path.dirname(__file__), '.env.aws')
if not os.path.exists(env_path):
    print(f"Error: Credentials file not found at {env_path}")
    print("Please create a .env.aws file in the root of the project with:")
    print("AWS_ACCESS_KEY_ID=your_access_key")
    print("AWS_SECRET_ACCESS_KEY=your_secret_key")
    print("AWS_DEFAULT_REGION=us-east-1")
    sys.exit(1)

load_dotenv(dotenv_path=env_path)

aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

if not aws_access_key or not aws_secret_key:
    print("Error: AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY is missing from .env.aws")
    sys.exit(1)

print(f"Initializing AWS Client in region: {region}...")
ec2_client = boto3.client(
    'ec2',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=region
)
ec2_resource = boto3.resource(
    'ec2',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=region
)

# Configuration names
KEY_NAME = "research-agent-key"
KEY_FILE = f"{KEY_NAME}.pem"
SG_NAME = "research-agent-sg"

# 1. Create or Load Key Pair
print("Configuring Key Pair...")
try:
    key_pair = ec2_client.create_key_pair(KeyName=KEY_NAME)
    private_key = key_pair['KeyMaterial']
    with open(KEY_FILE, 'w') as f:
        f.write(private_key)
    os.chmod(KEY_FILE, 0o600)
    print(f"Created new Key Pair and saved to {KEY_FILE}")
except ec2_client.exceptions.ClientError as e:
    if "InvalidKeyPair.Duplicate" in str(e):
        print(f"Key Pair '{KEY_NAME}' already exists on AWS. Using it (ensure you have the local {KEY_FILE} file).")
    else:
        raise e

# 2. Create Security Group
print("Configuring Security Group...")
try:
    sg_response = ec2_client.create_security_group(
        GroupName=SG_NAME,
        Description="Security Group for Research Agent App"
    )
    sg_id = sg_response['GroupId']
    print(f"Created Security Group: {sg_id}")
    
    # Authorize ingress rules
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Allow SSH'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Allow HTTP'}]
            }
        ]
    )
    print("Authorized SSH (22) and HTTP (80) traffic.")
except ec2_client.exceptions.ClientError as e:
    if "InvalidGroup.Duplicate" in str(e):
        sgs = ec2_client.describe_security_groups(GroupNames=[SG_NAME])
        sg_id = sgs['SecurityGroups'][0]['GroupId']
        print(f"Security Group '{SG_NAME}' already exists. Using: {sg_id}")
    else:
        raise e

# 3. Find latest Ubuntu 24.04 LTS AMI
print("Finding Ubuntu 24.04 LTS AMI...")
ami_response = ec2_client.describe_images(
    Filters=[
        {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*']},
        {'Name': 'state', 'Values': ['available']}
    ],
    Owners=['099720109477'] # Canonical owner ID
)
images = sorted(ami_response['Images'], key=lambda x: x['CreationDate'], reverse=True)
if not images:
    # Fallback to Ubuntu 22.04 if 24.04 not found
    print("Ubuntu 24.04 not found, checking Ubuntu 22.04 LTS...")
    ami_response = ec2_client.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
            {'Name': 'state', 'Values': ['available']}
        ],
        Owners=['099720109477']
    )
    images = sorted(ami_response['Images'], key=lambda x: x['CreationDate'], reverse=True)

ami_id = images[0]['ImageId']
print(f"Selected AMI: {ami_id} ({images[0]['Name']})")

# 4. User Data Script to install Docker
USER_DATA = """#!/bin/bash
set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== System Update ==="
apt-get update -y
apt-get upgrade -y

echo "=== Create Swap File (2GB) ==="
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "=== Install Docker ==="
apt-get install -y ca-certificates curl gnupg lsb-release
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu
apt-get install -y git
echo "=== Setup complete! ==="
"""

# 5. Launch Instance
print("Launching EC2 instance...")
instances = ec2_resource.create_instances(
    ImageId=ami_id,
    MinCount=1,
    MaxCount=1,
    InstanceType='t3.small', # 2 vCPU, 2GB RAM
    KeyName=KEY_NAME,
    SecurityGroupIds=[sg_id],
    UserData=USER_DATA,
    BlockDeviceMappings=[
        {
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'VolumeSize': 20, # 20 GB Disk
                'VolumeType': 'gp3',
                'DeleteOnTermination': True
            }
        }
    ]
)
instance = instances[0]
print(f"Instance requested. ID: {instance.id}")
print("Waiting for instance to start running...")
instance.wait_until_running()
instance.reload()

public_ip = instance.public_ip_address
print(f"\n🎉 EC2 Instance is running!")
print(f"Public IP: {public_ip}")
print(f"Public DNS: {instance.public_dns_name}")
print("Waiting for Docker installation to complete (takes 2-3 minutes)...")

# 6. Wait for SSH & User Data script to complete
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Try connecting via SSH until successful
retries = 30
connected = False
for i in range(retries):
    try:
        ssh_client.connect(
            hostname=public_ip,
            username='ubuntu',
            key_filename=KEY_FILE,
            timeout=10
        )
        connected = True
        print("SSH connection established successfully.")
        break
    except Exception:
        print(f"Waiting for SSH to become available ({i+1}/{retries})...")
        time.sleep(10)

if not connected:
    print("Error: Could not connect to the instance via SSH. Please verify security groups and key files.")
    sys.exit(1)

# Check user-data status
print("Checking status of Docker & system configuration...")
while True:
    stdin, stdout, stderr = ssh_client.exec_command('tail -n 1 /var/log/user-data.log')
    last_line = stdout.read().decode().strip()
    if "=== Setup complete! ===" in last_line:
        print("Docker setup is complete on the EC2 instance!")
        break
    else:
        print("Docker installation still in progress... (waiting 15s)")
        time.sleep(15)

# 7. Git clone and build
print("Cloning repository on instance...")
ssh_client.exec_command('rm -rf app')
stdin, stdout, stderr = ssh_client.exec_command('git clone https://github.com/Narendra02053/research-agent-.git app')
exit_status = stdout.channel.recv_exit_status()
if exit_status != 0:
    print("Error cloning repository:")
    print(stderr.read().decode())
    sys.exit(1)

# 8. Upload local .env variables
print("Configuring environment variables...")
local_env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
if os.path.exists(local_env_path):
    with open(local_env_path, 'r') as f:
        env_content = f.read()
    
    # Write environment variables to backend/.env on the EC2 instance
    sftp = ssh_client.open_sftp()
    with sftp.file('/home/ubuntu/app/backend/.env', 'w') as remote_file:
        remote_file.write(env_content)
    sftp.close()
    print("Uploaded backend/.env successfully.")
else:
    print("Warning: Local backend/.env file not found. Copying .env.example instead.")
    ssh_client.exec_command('cp app/backend/.env.example app/backend/.env')

# 9. Modify docker-compose.yml to serve frontend on port 80
print("Updating docker-compose.yml configuration to bind frontend to port 80...")
ssh_client.exec_command("sed -i 's/\"3000:80\"/\"80:80\"/g' app/docker-compose.yml")

# 10. Start application
print("Starting application containers...")
stdin, stdout, stderr = ssh_client.exec_command('cd app && docker compose up -d')
exit_status = stdout.channel.recv_exit_status()
if exit_status == 0:
    print("\n🚀 SUCCESS! Application has been started successfully!")
    print(f"Access your application at: http://{public_ip}")
    print("\nContainer status:")
    stdin, stdout, stderr = ssh_client.exec_command('cd app && docker compose ps')
    print(stdout.read().decode())
else:
    print("Error starting containers:")
    print(stderr.read().decode())

ssh_client.close()
