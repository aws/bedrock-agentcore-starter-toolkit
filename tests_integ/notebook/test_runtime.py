if __name__ == "__main__":
    from bedrock_agentcore_starter_toolkit import Runtime

    runtime = Runtime()

    runtime.configure(
        entrypoint="tests_integ/strands_agent/agent_example.py",
        execution_role="arn:aws:iam::381492293490:role/Admin",  # replace with your own role
        agent_name="agent_example_notebook_runtime",
    )

    resp = runtime.launch(local=True)
    print(resp)
