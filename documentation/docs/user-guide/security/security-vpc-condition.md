# Use IAM condition keys with AgentCore Runtime and built-in tools VPC settings

You can use Amazon Bedrock AgentCore-specific condition keys for VPC settings to
provide additional permission controls for your AgentCore Runtime and
built-in tools. For example, you can require that all runtimes in your organization are connected
to a VPC. You can also specify the subnets and security groups that users of the AgentCore Runtime can and
can't use.

AgentCore supports the following condition keys in IAM
policies:

* **bedrock-agentcore:subnets** – Allow or deny one or more
  subnets.
* **bedrock-agentcore:securityGroups** – Allow or deny one or
  more security groups.

The AgentCore Control Plane API operations
`CreateAgentRuntime`, `UpdateAgentRuntime`,
`CreateCodeInterpreter`, and `CreateBrowser` support these condition keys.
For more information about using condition keys in IAM policies, see [IAM JSON Policy Elements: Condition](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html "https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html") in the IAM User Guide.

## Example policies with condition keys for VPC settings

The following examples demonstrate how to use condition keys for VPC settings. After you
create a policy statement with the desired restrictions, attach the policy statement to the
target user or role.

### Require that users deploy only VPC-connected runtimes and tools

To require that all users deploy only VPC-connected AgentCore Runtime and built-in tools, you can
deny runtime and tool create and update operations that don't include valid subnets and
security groups.

```
{
  "Version": "2012-10-17"		 	 	 ,
  "Statement": [
    {
      "Sid": "EnforceVPCRuntime",
      "Action": [
        "bedrock-agentcore:CreateAgentRuntime",
        "bedrock-agentcore:UpdateAgentRuntime",
        "bedrock-agentcore:CreateCodeInterpreter",
        "bedrock-agentcore:CreateBrowser"
      ],
      "Effect": "Deny",
      "Resource": "*",
      "Condition": {
        "Null": {
          "bedrock-agentcore:Subnets": "true",
          "bedrock-agentcore:SecurityGroups": "true"
        }
      }
    }
  ]
}
```

### Deny users access to specific subnets or security groups

To deny users access to specific subnets, use `StringEquals` to check the value
of the `bedrock-agentcore:subnets` condition. The following example denies users
access to `subnet-1` and `subnet-2`.

```
{
  "Sid": "EnforceOutOfSubnet",
  "Action": [
    "bedrock-agentcore:CreateAgentRuntime",
    "bedrock-agentcore:UpdateAgentRuntime",
    "bedrock-agentcore:CreateCodeInterpreter",
    "bedrock-agentcore:CreateBrowser"
  ],
  "Effect": "Deny",
  "Resource": "*",
  "Condition": {
    "ForAnyValue:StringEquals": {
      "bedrock-agentcore:subnets": ["subnet-1", "subnet-2"]
    }
  }
}
```

To deny users access to specific security groups, use `StringEquals` to check
the value of the `bedrock-agentcore:securityGroups` condition. The following example
denies users access to `sg-1` and `sg-2`.

```
{
  "Sid": "EnforceOutOfSecurityGroups",
  "Action": [
    "bedrock-agentcore:CreateAgentRuntime",
    "bedrock-agentcore:UpdateAgentRuntime",
    "bedrock-agentcore:CreateCodeInterpreter",
    "bedrock-agentcore:CreateBrowser"
  ],
  "Effect": "Deny",
  "Resource": "*",
  "Condition": {
    "ForAnyValue:StringEquals": {
      "bedrock-agentcore:securityGroups": ["sg-1", "sg-2"]
    }
  }
}
```

### Allow users to create and update AgentCore Runtimes and tools with specific VPC settings

To allow users to access specific subnets, use `StringEquals` to check the
value of the `bedrock-agentcore:subnets` condition. The following example allows
users to access `subnet-1` and `subnet-2`.

```
{
  "Sid": "EnforceStayInSpecificSubnets",
  "Action": [
    "bedrock-agentcore:CreateAgentRuntime",
    "bedrock-agentcore:UpdateAgentRuntime",
    "bedrock-agentcore:CreateCodeInterpreter",
    "bedrock-agentcore:CreateBrowser"
  ],
  "Effect": "Allow",
  "Resource": "*",
  "Condition": {
    "ForAllValues:StringEquals": {
      "bedrock-agentcore:subnets": ["subnet-1", "subnet-2"]
    }
  }
}
```

To allow users to access specific security groups, use `StringEquals` to check
the value of the `bedrock-agentcore:SecurityGroups` condition. The following example
allows users to access `sg-1` and `sg-2`.

```
{
  "Sid": "EnforceStayInSpecificSecurityGroups",
  "Action": [
    "bedrock-agentcore:CreateAgentRuntime",
    "bedrock-agentcore:UpdateAgentRuntime",
    "bedrock-agentcore:CreateCodeInterpreter",
    "bedrock-agentcore:CreateBrowser"
  ],
  "Effect": "Allow",
  "Resource": "*",
  "Condition": {
    "ForAllValues:StringEquals": {
      "bedrock-agentcore:SecurityGroups": ["sg-1", "sg-2"]
    }
  }
}
```
