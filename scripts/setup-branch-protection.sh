#!/bin/bash
# Script to set up branch protection rules
# Usage: ./scripts/setup-branch-protection.sh <github-token>

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <github-token>"
    echo "Generate a token at: https://github.com/settings/tokens/new with repo scope"
    exit 1
fi

GITHUB_TOKEN=$1
REPO_OWNER="aws"
REPO_NAME="bedrock-agentcore-starter-toolkit-staging"
API_URL="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/branches"

# Read the branch protection configuration
CONFIG_FILE=".github/branch-protection.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found"
    exit 1
fi

# Function to apply branch protection
apply_branch_protection() {
    local branch=$1
    local config=$2

    echo "Applying protection rules to branch: $branch"

    curl -X PUT \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        -d "$config" \
        "$API_URL/$branch/protection"

    echo "Branch protection applied to $branch"
}

# Apply protection to main branch
MAIN_CONFIG=$(jq '.main' $CONFIG_FILE)
apply_branch_protection "main" "$MAIN_CONFIG"

echo "Branch protection setup complete!"
