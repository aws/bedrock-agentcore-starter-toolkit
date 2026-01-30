# Import Agent Design

Design overview for the import-agent utility, explaining the choices behind the generated agent.


## Utility Feature Support

Below is each feature of Bedrock Agents and which of the features this utility successfully maps to each target framework. We also describe which AgentCore Primitive is used to enhance each feature mapping.

|Bedrock Agent Feature	|AgentCore + Langchain	|AgentCore + Strands	|Notes	|
|---	|---	|---	|---	|
|Action Groups	|SUPPORTED	|SUPPORTED	|Uses AgentCore Gateway	|
|Orchestration	|SUPPORTED	|SUPPORTED	|	|
|*Guardrails*	|SUPPORTED	|SUPPORTED	|	|
|*Knowledge Bases*	|SUPPORTED	|SUPPORTED	|	|
|*Code Interpreter*	|SUPPORTED	|SUPPORTED	|Uses AgentCore Code Interpreter	|
|Short Term Memory	|SUPPORTED	|SUPPORTED	|	|
|Long Term Memory	|SUPPORTED	|SUPPORTED	|Uses AgentCore Memory	|
|Pre/Post Processing Step	|SUPPORTED	|SUPPORTED	|	|
|User Input	|SUPPORTED	|SUPPORTED	|	|
|*Traces*	|SUPPORTED	|SUPPORTED	|Uses AgentCore Observability	|
|Multi-Agent Collaboration 	|SUPPORTED	|SUPPORTED	|	|

## Action Groups → AgentCore Gateway Target

In Bedrock Agents, users can define Action Groups for their agents. An Action Group is a collection of tools that are either executed via AWS Lambda or through a local callback (Return of Control). These tools are defined using either an OpenAPI specification or a structured function schema. At runtime, Bedrock Agents call your Lambda function with an event formatted according to the schema you selected. The structure of this event is documented here: [AWS Bedrock Lambda integration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html).

In AgentCore Gateway, we create one gateway per generated agent. Each Action Group in Bedrock Agents maps to a target in the gateway. Within each target, every function or path/method becomes a tool. To ensure compatibility with existing Action Group Lambda functions, we use a proxy Lambda function as the executor for all tools in the gateway. This proxy:

1. Receives tool calls in the Gateway's format.
2. Identifies the correct Action Group Lambda to invoke.
3. Reformats the request object to match the expected format.
4. Calls the appropriate Lambda and returns the result in a Gateway-compatible format.

If AgentCore Gateway is disabled, the system generates local tools instead:

* Each function or path/method becomes a separate tool.
* The tool’s argument schema is exposed to the agent via Pydantic model generation.
* Each tool formats its request correctly and calls the corresponding Action Group Lambda directly.

This approach also applies to Return of Control (ROC) action groups, where the tool prompts the user for input locally before proceeding with execution.


## Orchestration

For orchestration, the Bedrock Agents prompt are constructed at runtime, by substituting in template fixtures (ie. variables in the prompt). For example, the orchestration prompt may have the fixture called knowledge_base_guidelines. This variable is filled in depending on the model provider and model version in use.

To approximate the same behavior and deliver translated agents that are functionally equivalent, the utility uses ONE collection of template fixtures (`template_fixtures_merged.json`) and substitutes them in to build the correct prompts. As for orchestration strategy, for both Langchain and Strands, the utility uses the standard ReAcT orchestration pattern.


## Guardrails

In Bedrock Agents, users can add Bedrock Guardrails to their agent. This applies the guardrail on the model level and Bedrock Agents will have defined behavior for when a guardrail is invoked to redact or block an input. Equivalently, the utility applies the same guardrail on Bedrock models, as there is support for this in both Langchain and Strands.


## Knowledge Bases

In Bedrock Agents, users can add existing Knowledge Bases (defined via Bedrock Knowledge Bases) to their agent via the Console or SDK. The AgentCore + Langchain/Strands equivalent of this feature is to use each of those KBs to define a KB retrieval tool for an agent to use. This tool uses the AWS SDK to retrieve from connected knowledge bases using a query decided by the agent and then returns the document results for the agent to use.


## Code Interpreter → AgentCore Code Interpreter

In Bedrock Agents, users can enable Code Interpreter. This gives a Bedrock Agent access to a sandbox for it to write, troubleshoot, and return the output of code.

We use AgentCore Code Interpreter for an equivalent experience. The utility defines a `code_tool` which creates a code sandbox session and defines a sub-agent with access to code interpreter operations (as tools). These operations include executing code, writing/removing files, and more. This sub-agent is fed the code tool's input query and runs in a loop using the sandbox operations to accomplish the coding task and return the output.

When AgentCore Code Interpreter is opted-out, we use open-interpreter, an open source and local code interpreter that can write, execute, and troubleshoot code.


## Short Term Memory

In Bedrock Agents, by default, agents have short term memory of an entire session’s messages. This means that the user can ask any number of questions within a session, with the agent keeping earlier messages from that session in its context.

The utility will use an in-memory saver as a solution for this. In Langchain, we use an in-memory store to save the session’s messages in a thread for that session. In Strands, we use a Sliding Conversation Manager, which can maintain in-memory context of any number of earlier messages in a session.


## Long Term Memory → AgentCore Memory

In Bedrock Agents, users can enable Long Term Memory for their agent. This is based on session summarization, where BR Agents uses an LLM to summarize the conversation’s discussion topics based on a session’s messages. This occurs on the end of each session, and customers can configure a max number of sessions and max days threshold to keep the summaries. In the orchestration prompt in BR agents, a synopsis of the long-term memory, consisting of multiple of these session summaries, is injected.

In Bedrock Agents, users can enable Long-Term Memory for their agents. This system is based on session summarization, where Bedrock Agents use an LLM to summarize discussion topics from each session’s messages.

* Summarization happens at the end of each session.
* Customers can configure:
    * The maximum number of sessions to retain.
    * A maximum age (in days) for how long to keep the summaries.
* During orchestration, Bedrock Agents inject a synopsis of long-term memory—which consists of multiple session summaries—into the system prompt.

In AgentCore Memory, the utility implements a similar memory model using a summarization strategy with a dedicated memory store:

```
{
    "summaryMemoryStrategy": {
        "name": "SessionSummarizer",
        "namespaces": ["/summaries/{actorId}/{sessionId}/"],
    }
}
```

On each entrypoint invocation, formatted messages are saved to this memory store by generating an event that includes the correct `userId` and `sessionId` (both provided to the entrypoint). During agent initialization (inside the `get_agent` loop in the output code), the top session summaries are retrieved from the memory store and formatted to match the Bedrock Agents' memory style. These formatted summaries are then injected into the agent's system prompt as a memory synopsis.

If AgentCore Memory is opted out, then we replicate the behavior with a local long term memory manager, which uses a memory summarization LLM and the memory summarization BR agents prompt to create and manage session summaries. The generated summaries are saved and maintained in a local session summaries JSON file.


## Pre/Post-Processing Step

In Bedrock Agents, customers can enable and override pre-processing and post-processing steps in their agents. These steps are meant to be taken at the start and end, respectively, of agent invocation.

If the pre-processing step is enabled, then within the `invoke_agent` function, the utility will use the pre-processing prompt on the user query and append the output to the query before passing this on to the orchestration loop. If the post-processing step is enabled, then the post-processing prompt is used on the orchestration loop output, and this result is returned as the output of `invoke_agent`.


## User Input

In Bedrock Agents, an agent can ask for human input. This may be for clarification or to ask for missing parameters for a tool call. If enabled, the utility will create a human input tool, which can be invoked with a question by the agent and asks the user for CLI input on that question. This answer is then returned to the agent as the tool’s output.


## Traces → AgentCore Observability

In Bedrock Agents, users can view traces that describe pre/post processing steps, routing classifier steps, guardrail invocation, agent orchestration, and other information. These traces are in a format specific to Bedrock Agents, and can be viewed either in the console or as output of an invoke_agent call to a BR agent.

The equivalent for this with AgentCore is to use AgentCore Observability (if not opted-out). For both Langchain and Strands, the agent will output OTEL logs on a session, trace, and span level. These logs are captured by AgentCore Observability when the agent is deployed to AgentCore Runtime, and the logs will be visible in CloudWatch under the GenAI Observability section.


## Multi-Agent Collaboration

In Bedrock Agents, users can promote an agent and add collaborators to it. This hierarchy can be up to 5 levels deep. A collaborator can receive shared conversation history from the parent, and can be invoked with routing mode (parent uses a routing classifier prompt to find a relevant collaborator for a user query) or supervisor mode (an agents-as-tools approach).

The utility's approach to this is to recursively translate a parent agent and its children, and then orchestrate them together via an Agents-as-Tools approach by default. If conversation sharing is enabled, then the parent will inject its state into the child's via these collaboration tools. If routing mode is enabled for the parent, then the parent agent uses a routing classifier prompt, before orchestration, to invoke a relevant child agent. In AgentCore Runtime, the code for a parent agent and its children are packaged together, in the same container image, to enable this setup.
