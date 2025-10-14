import os

TEST_ROLE = None
TEST_ECR = os.getenv("AGENTCORE_TEST_ECR", default="auto")
