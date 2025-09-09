#!/usr/bin/env python3
"""
Lambda function to run tests directly - bypassing CodeBuild entirely
Achieves <10s test execution by eliminating build overhead
"""

import json
import os
import subprocess
import sys
import time
import zipfile

import boto3


def lambda_handler(event, context):
    """
    Run pytest directly in Lambda environment
    No container build needed - just execute tests
    """
    start_time = time.time()

    # Download source if needed
    if event.get("source_s3"):
        download_source(event["source_s3"])

    # Install test dependencies (cached in Lambda container)
    print(f"Installing dependencies... {time.time() - start_time:.2f}s")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "pytest", "pytest-asyncio", "moto", "--target", "/tmp/deps"]
    )
    sys.path.insert(0, "/tmp/deps")

    # Run tests
    print(f"Running tests... {time.time() - start_time:.2f}s")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"], capture_output=True, text=True, cwd="/tmp/source"
    )

    elapsed = time.time() - start_time

    return {
        "statusCode": 200 if result.returncode == 0 else 400,
        "body": json.dumps(
            {
                "duration_seconds": elapsed,
                "test_output": result.stdout[-4000:],  # Last 4KB of output
                "errors": result.stderr[-1000:] if result.stderr else None,
                "exit_code": result.returncode,
            }
        ),
    }


def download_source(s3_path):
    """Download and extract source from S3"""
    s3 = boto3.client("s3")
    bucket, key = s3_path.replace("s3://", "").split("/", 1)

    # Download to /tmp
    s3.download_file(bucket, key, "/tmp/source.zip")

    # Extract
    os.makedirs("/tmp/source", exist_ok=True)
    with zipfile.ZipFile("/tmp/source.zip", "r") as zip_ref:
        zip_ref.extractall("/tmp/source")


# Lambda deployment configuration
LAMBDA_CONFIG = {
    "FunctionName": "bedrock-agentcore-test-runner",
    "Runtime": "python3.10",
    "Handler": "lambda_test_runner.lambda_handler",
    "Timeout": 900,  # 15 minutes max
    "MemorySize": 3008,  # Maximum for fastest CPU
    "Environment": {"Variables": {"PYTHONPATH": "/tmp/deps:/tmp/source"}},
    "EphemeralStorage": {
        "Size": 10240  # 10GB storage
    },
}
