if __name__ == "__main__":
    from bedrock_agentcore_starter_toolkit import Runtime

    runtime = Runtime()

    runtime.configure(entrypoint="agent_example.py", agent_name="test14", auto_create_execution_role=True)

    resp = runtime.launch(use_codebuild=True, auto_update_on_conflict=True)
    print(resp)
