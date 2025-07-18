# Getting Started with AgentCore Identity

Amazon Bedrock AgentCore Identity provides a secure way to manage identities for your AI agents and enable authenticated access to external services. This guide will help you get started with implementing identity features in your agent applications.

## Prerequisites

Before you begin, ensure you have:

- An AWS account with appropriate permissions
- Python 3.10+ installed
- AWS CLI configured with your credentials
- (Optional) External service accounts for OAuth2 or API key integration

## Install the SDK

```bash
pip install bedrock-agentcore
```

## Create a Workload Identity

A workload identity is a unique identifier that represents your agent within the AgentCore Identity system:

```python
from bedrock_agentcore.services.identity import IdentityClient

# Create identity client
identity_client = IdentityClient("us-east-1")

# Create workload identity
workload_identity = identity_client.create_workload_identity(
    name="my-research-agent",
)

print(f"Workload Identity ARN: {workload_identity['workloadIdentityArn']}")
print(f"Agent Name: {workload_identity['name']}")
```

You can also use the AWS CLI:

```bash
aws bedrock-agentcore create-workload-identity \
    --name "my-research-agent"
```

## Configure Credential Providers

Credential providers define how your agent accesses external services:

### OAuth2 Provider Example (Google)

```python
# Configure Google OAuth2 provider
google_provider = identity_client.create_oauth2_credential_provider(req={
    "name": "myGoogleCredentialProvider",
    "credentialProviderVendor": "GoogleOauth2",
    "oauth2ProviderConfigInput": {
        "googleOauth2ProviderConfig": {
            "clientId": "your-google-client-id",
            "clientSecret": "your-google-client-secret"
        }
    }
})
```

### API Key Provider Example (Perplexity AI)

```python
# Configure API key provider
perplexity_provider = identity_client.create_api_key_credential_provider(req={
    "name": "myPerplexityAPIKeyCredentialProvider",
    "apiKey": "myApiKey"
})
```

## Configure Environment Variables

Set up environment variables for your development environment:

```bash
# AWS Configuration
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Agent Configuration
export AGENT_IDENTITY_ID=your-agent-identity-id
export AGENT_IDENTITY_ARN=your-agent-identity-arn
export WORKLOAD_ACCESS_TOKEN=your-workload-access-token
```

## Building a Simple Research Agent

Let's create a simple research agent that demonstrates AgentCore Identity capabilities:

### Agent Implementation

Create a file named `research_agent.py`:

```python
# research_agent.py
import os
import asyncio
from typing import Optional
from datetime import datetime
from bedrock_agentcore.services.identity import IdentityClient
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests

class ResearchAgent:
    def __init__(self):
        self.identity_client = IdentityClient("us-east-1")
        self.workload_token = os.getenv('WORKLOAD_ACCESS_TOKEN')

    async def search_web(self, query: str) -> str:
        """Search the web using Perplexity AI"""
        # Get API key from identity service
        api_key = await self.identity_client.get_api_key(
            provider_name="myPerplexityAPIKeyCredentialProvider",
            agent_identity_token=self.workload_token
        )

        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "sonar",
            "messages": [
                {"role": "user", "content": query}
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Search error: {str(e)}"

    async def save_to_drive(self, content: str, filename: str) -> str:
        """Save content to Google Drive"""
        try:
            # Get OAuth2 access token from identity service
            access_token = await self.identity_client.get_token(
                provider_name="myGoogleCredentialProvider",
                scopes=["https://www.googleapis.com/auth/drive.file"],
                agent_identity_token=self.workload_token,
                auth_flow="USER_FEDERATION",
                callback_url="https://myapp.com/callback"
            )

            # Create Google Drive service
            creds = Credentials(token=access_token)
            service = build("drive", "v3", credentials=creds)

            # Create file metadata
            file_metadata = {
                'name': filename,
                'mimeType': 'text/plain'
            }

            # Upload file
            from googleapiclient.http import MediaIoBaseUpload
            import io

            media = MediaIoBaseUpload(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/plain'
            )

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()

            return f"File saved to Google Drive: {file.get('webViewLink')}"

        except Exception as e:
            return f"Drive save error: {str(e)}"

    async def research_and_save(self, topic: str, user_id: str = None) -> str:
        """Main agent function: research a topic and save to Drive"""
        try:
            # Search for information
            search_query = f"Research comprehensive information about: {topic}"
            search_results = await self.search_web(search_query)

            # Format the research report
            report = f"""
Research Report: {topic}
Generated by Research Agent
{'=' * 50}

{search_results}

{'=' * 50}
Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            # Save to Google Drive
            filename = f"research_report_{topic.replace(' ', '_')}.txt"

            save_result = await self.save_to_drive(
                content=report,
                filename=filename
            )

            return f"Research completed! {save_result}"

        except Exception as e:
            return f"Research failed: {str(e)}"

# Create agent instance
agent = ResearchAgent()
```

### Create HTTP Server

Create a file named `server.py` to host your agent:

```python
# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from research_agent import agent

app = FastAPI(title="Research Agent API")

class ResearchRequest(BaseModel):
    topic: str
    user_id: Optional[str] = None

@app.post("/research")
async def research_endpoint(request: ResearchRequest):
    """Research a topic and save results to Google Drive"""
    try:
        result = await agent.research_and_save(
            topic=request.topic,
            user_id=request.user_id
        )
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
```

### Test Your Agent

Start your agent server:

```bash
python server.py
```

Test the agent using curl:

```bash
# Test health endpoint
curl http://localhost:8080/health

# Test research functionality
curl -X POST http://localhost:8080/research \
    -H "Content-Type: application/json" \
    -d '{
        "topic": "artificial intelligence trends 2024",
        "user_id": "user123"
    }'
```

## Understanding the OAuth2 Authorization Flow

When your agent first attempts to access Google Drive, it will trigger a 3-legged OAuth (3LO) flow:

1. The AgentCore SDK will display a URL for authentication
2. The user visits the URL and grants permissions
3. The token is securely stored in the token vault
4. Subsequent requests use the cached token

Example output during the OAuth2 flow:

```
Waiting for authentication...
Visit the following URL to login:
https://bedrock-agentcore.us-west-2.amazonaws.com/identities/oauth2/authorize?request_uri=123456789

Polling for token... (press Ctrl+C to cancel)
```

## Using Declarative Annotations

For a cleaner implementation, you can use AgentCore Identity's declarative annotations:

```python
from bedrock_agentcore.identity import requires_access_token, requires_api_key

@requires_api_key(provider="Perplexity AI")
def search_perplexity(query, api_key=None):
    """
    Search Perplexity AI with the query.
    The api_key is automatically injected by the @requires_api_key decorator.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    # Make API call to Perplexity AI with the headers
    # ...
    return results

@requires_access_token(provider="Google Workspace", scopes=["https://www.googleapis.com/auth/drive.file"])
def save_to_google_drive(content, filename, access_token=None):
    """
    Save content to Google Drive.
    The access_token is automatically injected by the @requires_access_token decorator.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    # Make API call to Google Drive with the headers
    # ...
    return results
```

## Security Best Practices

When working with identity information:

1. **Never hardcode credentials** in your agent code
2. **Use environment variables or AWS Secrets Manager** for sensitive information
3. **Apply least privilege principle** when configuring IAM permissions
4. **Regularly rotate credentials** for external services
5. **Audit access logs** to monitor agent activity
6. **Implement proper error handling** for authentication failures
