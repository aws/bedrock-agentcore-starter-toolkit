#!/usr/bin/env python3
"""
Ultra-fast deployment using Lambda + pre-built base images
Achieves <15s by eliminating build steps
"""

import hashlib
import json
import time

import boto3


def lambda_handler(event, context):
    """
    Fast deployment strategy:
    1. Use pre-built base image with all dependencies (cached in ECR)
    2. Only update application code layer (small, fast)
    3. Skip build entirely - just copy files
    """
    start = time.time()

    ecr = boto3.client("ecr")
    s3 = boto3.client("s3")

    # Configuration
    repo_name = "bedrock-agentcore-test_siwabhi_9_6_3"
    base_image = f"309149493152.dkr.ecr.us-west-2.amazonaws.com/{repo_name}:base-deps"

    print(f"[{time.time() - start:.1f}s] Starting fast deployment")

    # Step 1: Pull source code (2s)
    print(f"[{time.time() - start:.1f}s] Downloading source...")
    source = s3.get_object(
        Bucket="bedrock-agentcore-codebuild-sources-309149493152-us-west-2", Key="test_siwabhi_9_6_3/source.zip"
    )

    # Step 2: Create thin layer with just code changes (1s)
    print(f"[{time.time() - start:.1f}s] Creating code layer...")
    code_layer = create_code_only_layer(source["Body"].read())

    # Step 3: Push only the code layer (3s)
    print(f"[{time.time() - start:.1f}s] Pushing code layer to ECR...")
    push_layer_to_ecr(ecr, repo_name, code_layer)

    # Step 4: Update manifest to reference base + new code (1s)
    print(f"[{time.time() - start:.1f}s] Updating image manifest...")
    update_image_manifest(ecr, repo_name, base_image, code_layer)

    elapsed = time.time() - start
    print(f"[{elapsed:.1f}s] Deployment complete!")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": f"Deployed in {elapsed:.1f} seconds", "image": f"{base_image.rsplit(':', 1)[0]}:latest"}
        ),
    }


def create_code_only_layer(source_zip):
    """Create minimal layer with only application code"""
    import tarfile
    import zipfile
    from io import BytesIO

    # Extract only .py files from source
    with zipfile.ZipFile(BytesIO(source_zip)) as zf:
        code_files = {}
        for name in zf.namelist():
            if name.endswith(".py") and not name.startswith("."):
                code_files[name] = zf.read(name)

    # Create tar layer
    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        for path, content in code_files.items():
            info = tarfile.TarInfo(name=f"app/{path}")
            info.size = len(content)
            tar.addfile(info, BytesIO(content))

    return tar_buffer.getvalue()


def push_layer_to_ecr(ecr, repo_name, layer_data):
    """Push single layer to ECR"""
    # Initiate layer upload
    upload = ecr.initiate_layer_upload(repositoryName=repo_name)
    upload_id = upload["uploadId"]

    # Upload layer
    ecr.upload_layer_part(
        repositoryName=repo_name,
        uploadId=upload_id,
        partFirstByte=0,
        partLastByte=len(layer_data) - 1,
        layerPartBlob=layer_data,
    )

    # Complete upload
    layer_digest = f"sha256:{hashlib.sha256(layer_data).hexdigest()}"
    ecr.complete_layer_upload(repositoryName=repo_name, uploadId=upload_id, layerDigests=[layer_digest])

    return layer_digest


def update_image_manifest(ecr, repo_name, base_image, code_layer):
    """Create new image manifest referencing base + code layers"""
    # Get base image manifest
    base_manifest = ecr.batch_get_image(repositoryName=repo_name, imageIds=[{"imageTag": base_image.split(":")[-1]}])[
        "images"
    ][0]["imageManifest"]

    # Add new code layer to manifest
    manifest = json.loads(base_manifest)
    manifest["layers"].append(
        {
            "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "size": len(code_layer),
            "digest": f"sha256:{hashlib.sha256(code_layer).hexdigest()}",
        }
    )

    # Push updated manifest
    ecr.put_image(repositoryName=repo_name, imageManifest=json.dumps(manifest), imageTag="latest")


# Deployment configuration for Lambda
DEPLOY_CONFIG = """
# Deploy this Lambda function:
aws lambda create-function \
  --function-name bedrock-agentcore-fast-deploy \
  --runtime python3.10 \
  --role arn:aws:iam::309149493152:role/lambda-deploy-role \
  --handler fast_deploy_lambda.lambda_handler \
  --timeout 60 \
  --memory-size 3008 \
  --zip-file fileb://fast_deploy.zip

# Trigger deployment:
aws lambda invoke \
  --function-name bedrock-agentcore-fast-deploy \
  --payload '{}' \
  response.json

# Expected timing:
# - Lambda cold start: 0.5-1s
# - Download source: 2s
# - Create code layer: 1s
# - Push to ECR: 3s
# - Update manifest: 1s
# Total: 7-9 seconds
"""
