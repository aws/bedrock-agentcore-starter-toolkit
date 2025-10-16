# Use interface VPC endpoints (AWS PrivateLink) to create a private connection between your VPC and your AgentCore resources

You can use AWS PrivateLink to create a private connection between your VPC and
Amazon Bedrock AgentCore. You can access AgentCore as if it were in your VPC, without the use of an
internet gateway, NAT device, VPN connection, or AWS Direct Connect connection. Instances in your VPC
don't need public IP addresses to access AgentCore.

You establish this private connection by creating an *interface
endpoint*, powered by AWS PrivateLink. We create an endpoint network interface
in each subnet that you enable for the interface endpoint. These are requester-managed
network interfaces that serve as the entry point for traffic destined for AgentCore.

For more information, see [Access AWS services
through AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html "https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html") in the
*AWS PrivateLink Guide*.

## Considerations for AgentCore

Before you set up an interface endpoint for AgentCore, review [Considerations](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#considerations-interface-endpoints "https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#considerations-interface-endpoints") in the *AWS PrivateLink Guide*.

AgentCore supports the following through interface endpoints:

* Data plane operations (runtime APIs)
* Invoking gateways

###### Note

AWS PrivateLink is currently not supported for Amazon Bedrock AgentCore control plane endpoints.

AgentCore interface endpoints are available in the following AWS Regions:

* US East (N. Virginia)
* US West (Oregon)
* Europe (Frankfurt)
* Asia Pacific (Sydney)

###### Authorization considerations for data plane APIs

The data plane APIs support both AWS Signature Version 4 (SigV4) headers for
authentication and Bearer Token (OAuth) authentication. VPC endpoint policies can
only restrict callers based on IAM principals and not OAuth users. For OAuth-based
requests to succeed through the VPC endpoint, the principal must be set to
`*` in the endpoint policy. Otherwise, only SigV4 allowlisted callers
can make successful calls over the VPC endpoint.

AWS IAM global condition context keys are supported. By default, full access to
AgentCore is allowed through the interface endpoint. You can control access by attaching
an endpoint policy to the interface endpoint or by associating a security group with the
endpoint network interfaces.

## Create an interface endpoint for AgentCore

You can create an interface endpoint for AgentCore using either the Amazon VPC console or
the AWS Command Line Interface (AWS CLI). For more information, see [Create an interface endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#create-interface-endpoint-aws "https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#create-interface-endpoint-aws") in the
*AWS PrivateLink Guide*.

Create an interface endpoint for AgentCore using the following service name
format:

* Data plane operations:
  `com.amazonaws.region.bedrock-agentcore`
* For AgentCore Gateway:
  `com.amazonaws.region.bedrock-agentcore.gateway`

If you enable private DNS for the interface endpoint, you can make API requests to
AgentCore using its default Regional DNS name. For example,
`bedrock-agentcore.us-east-1.amazonaws.com`.

## Create an endpoint policy for your interface endpoint

An endpoint policy is an IAM resource that you can attach to an interface endpoint.
The default endpoint policy allows full access to AgentCore through the interface
endpoint. To control the access allowed to AgentCore from your VPC, attach a custom
endpoint policy to the interface endpoint.

An endpoint policy specifies the following information:

* The principals that can perform actions (AWS accounts, IAM users, and
  IAM roles).

  + For AgentCore Gateway, if your gateway ingress isn't [AWS
    Signature Version 4 (SigV4)](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html "https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html")-based (for example, if you use
    OAuth instead), you must specify the `Principal` field as the
    wildcard `*`. SigV4 -based authentication allows you to
    define the `Principal` as a specific AWS identity.
* The actions that can be performed.
* The resources on which the actions can be performed.

For more information, see [Control access to services using endpoint policies](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html "https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html") in the
*AWS PrivateLink Guide*.

###### Endpoint policies for various primitives

The following examples show endpoint policies for different AgentCore components:

Runtime
:   The following endpoint policy allows specific IAM principals to invoke agent runtime resources.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:user/USERNAME"
             },
             "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:runtime/RUNTIME_ID"
          }
       ]
    }
    ```

    ###### Mixed IAM and OAuth authentication

    The `InvokeAgentRuntime` API supports two modes of VPC endpoint authorization. The following example policy allows both IAM principals and OAuth callers to access different agent runtime resources.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:root"
             },
             "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:runtime/customAgent1"
          },
          {
             "Effect": "Allow",
             "Principal": "*",
             "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:runtime/customAgent2"
          }
       ]
    }
    ```

    The above policy allows only the IAM principal to make `InvokeAgentRuntime` calls to `customAgent1`. It also allows both IAM principals and OAuth callers to make `InvokeAgentRuntime` calls to `customAgent2`.

Code Interpreter
:   The following endpoint policy allows specific IAM principals to invoke Code Interpreter resources.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:root"
             },
             "Action": [
                "bedrock-agentcore:InvokeCodeInterpreter"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:code-interpreter/CODE_INTERPRETER_ID"
          }
       ]
    }
    ```

Memory
:   ###### All data plane operations

    The following endpoint policy allows specific IAM principals to access us-east-1 data plane operations
    for a specific AgentCore Memory.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:root"
             },
             "Action": [
                "bedrock-agentcore:CreateEvent",
                "bedrock-agentcore:DeleteEvent",
                "bedrock-agentcore:GetEvent",
                "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:DeleteMemoryRecord",
                "bedrock-agentcore:GetMemoryRecord",
                "bedrock-agentcore:ListMemoryRecords",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:ListActors",
                "bedrock-agentcore:ListSessions",
                "bedrock-agentcore:BatchCreateMemoryRecords",
                "bedrock-agentcore:BatchDeleteMemoryRecords",
                "bedrock-agentcore:BatchUpdateMemoryRecords"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:memory/MEMORY_ID"
          }
       ]
    }
    ```

    ###### Access to all memories

    The following endpoint policy allows specific IAM principals access to all memories.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:root"
             },
             "Action": [
                "bedrock-agentcore:CreateEvent",
                "bedrock-agentcore:DeleteEvent",
                "bedrock-agentcore:GetEvent",
                "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:DeleteMemoryRecord",
                "bedrock-agentcore:GetMemoryRecord",
                "bedrock-agentcore:ListMemoryRecords",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:ListActors",
                "bedrock-agentcore:ListSessions",
                "bedrock-agentcore:BatchCreateMemoryRecords",
                "bedrock-agentcore:BatchDeleteMemoryRecords",
                "bedrock-agentcore:BatchUpdateMemoryRecords"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:memory/*"
          }
       ]
    }
    ```

    ###### Access restriction by APIs

    The following endpoint policy grants permission for a specific IAM principal to create events in a
    specific AgentCore Memory resource.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:root"
             },
             "Action": [
                "bedrock-agentcore:CreateEvent"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:memory/MEMORY_ID"
          }
       ]
    }
    ```

Browser Tool
:   The following endpoint policy allows specific IAM principals to connect to Browser Tool resources.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": {
                "AWS": "arn:aws::iam::ACCOUNT_ID:root"
             },
             "Action": [
                "bedrock-agentcore:ConnectBrowserAutomationStream"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1:ACCOUNT_ID:browser/BROWSER_ID"
          }
       ]
    }
    ```

Gateway
:   The following is an example of a custom endpoint policy. When you attach this policy to your interface endpoint, it allows all principals to invoke the gateway specified in the `Resource` field.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": "*",
             "Action": [
                "bedrock:InvokeGateway"
             ],
             "Resource": "arn:aws::bedrock-agentcore:us-east-1::gateway/my-gateway"
          }
       ]
    }
    ```

Identity
:   The following endpoint policy allows access to Identity resources.

    ```
    {
       "Statement": [
          {
             "Effect": "Allow",
             "Principal": "*",
             "Action": [
                "*"
             ],
             "Resource": "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT_ID:workload-identity-directory/default/workload-identity/WORKLOAD_IDENTITY_ID"
          }
       ]
    }
    ```
