import os

TEST_ROLE = os.getenv("AGENTCORE_TEST_ROLE", default="Admin")
TEST_ECR = os.getenv("AGENTCORE_TEST_ECR", default="auto")
