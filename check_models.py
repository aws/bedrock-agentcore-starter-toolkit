#!/usr/bin/env python3
"""Check available Bedrock models"""

import boto3
from dotenv import load_dotenv

load_dotenv()

def check_available_models():
    """List available Bedrock models"""
    try:
        bedrock = boto3.client('bedrock', region_name='us-east-1')
        
        print("Checking available foundation models...")
        response = bedrock.list_foundation_models()
        
        available_models = []
        for model in response['modelSummaries']:
            if model['modelLifecycle']['status'] == 'ACTIVE':
                available_models.append({
                    'id': model['modelId'],
                    'name': model['modelName'],
                    'provider': model['providerName']
                })
        
        print(f"\nFound {len(available_models)} available models:")
        for model in available_models:
            print(f"- {model['provider']}: {model['name']} ({model['id']})")
            
        return available_models
        
    except Exception as e:
        print(f"Error checking models: {e}")
        return []

if __name__ == "__main__":
    check_available_models()