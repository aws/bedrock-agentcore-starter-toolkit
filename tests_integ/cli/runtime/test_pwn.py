import os

def test_pwn():
    print("PWN_TEST:", os.environ.get("AWS_ACCESS_KEY_ID") is not None)
