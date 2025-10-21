# Configure Amazon Bedrock AgentCore Runtime and tools for VPC

You can configure Amazon Bedrock AgentCore Runtime and built-in tools (Code Interpreter and Browser Tool) to connect to resources in your Amazon Virtual Private Cloud (VPC). By configuring VPC connectivity, you enable secure access to private resources such as databases, internal APIs, and services within your VPC.

## VPC connectivity for Amazon Bedrock AgentCore Runtime and tools

To enable Amazon Bedrock AgentCore Runtime and built-in tools to securely access resources in your private VPC, Amazon Bedrock AgentCore provides VPC connectivity capabilities. This feature allows your runtime and tools to:

* Connect to private resources without exposing them to the internet
* Maintain secure communications within your organization's network boundaries
* Access enterprise data stores and internal services while preserving security

When you configure VPC connectivity for Amazon Bedrock AgentCore Runtime and tools:

* Amazon Bedrock creates elastic network interfaces (ENIs) in your VPC using the service-linked role
  `AWSServiceRoleForBedrockAgentCoreNetwork`
* These ENIs enable your Amazon Bedrock AgentCore Runtime and tools to securely communicate with resources in your VPC
* Each ENI is assigned a private IP address from the subnets you specify
* Security groups attached to the ENIs control which resources your runtime and tools can communicate with

###### Note

VPC connectivity impacts only outbound network traffic from the runtime or tool. Inbound
requests to the runtime (such as invocations) are not routed through the VPC and are unaffected
by this configuration.

## Prerequisites

Before configuring Amazon Bedrock AgentCore Runtime and tools for VPC access, ensure you have:

* An Amazon VPC with appropriate subnets for your runtime and tool requirements. For example, to configure your subnets to have internet access, see [Internet access considerations](#agentcore-internet-access "#agentcore-internet-access").
* Subnets located in supported Availability Zones for your region. For information about supported Availability Zones, see [Supported Availability Zones](#agentcore-supported-azs "#agentcore-supported-azs").
* Appropriate security groups defined in your VPC for runtime and tool access patterns. For example, to configure your security groups to connect to Amazon RDS, see [Example: Connecting to an Amazon RDS database](#agentcore-security-groups-example "#agentcore-security-groups-example").
* Required IAM permissions to create and manage the service-linked role (already included in the
  AWS managed policy [BedrockAgentCoreFullAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html "https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html")). For information about required permissions, see [IAM permissions](#agentcore-iam-permissions "#agentcore-iam-permissions").
* Required VPC endpoints if your VPC doesn't have internet access. For example, to configure your VPC endpoints, see [VPC endpoint configuration](#agentcore-vpc-endpoints "#agentcore-vpc-endpoints").
* Understanding of your runtime and tool network requirements (databases, APIs, web resources). If you need to use Browser tool which requires internet access, then your VPC should have internet access through
  NAT Gateway. For example, see [Security group considerations](#agentcore-security-groups "#agentcore-security-groups").

###### Important

Amazon Bedrock AgentCore creates a network interface in your account with a private IP address. Using a public subnet does not provide internet connectivity.
To enable internet access, place it in private subnets with a route to a NAT Gateway.

## Supported Availability Zones

Amazon Bedrock AgentCore supports VPC connectivity in specific Availability Zones within each supported region. When configuring subnets for your Amazon Bedrock AgentCore Runtime and built-in tools, ensure that your subnets are located in the supported Availability Zones for your region.

The following table shows the supported Availability Zone IDs for each region:

| Region | Region Code | Supported Availability Zones |
| --- | --- | --- |
| US East (N. Virginia) | us-east-1 | * use1-az1 * use1-az2 * use1-az4 |
| US East (Ohio) | us-east-2 | * use2-az1 * use2-az2 * use2-az3 |
| US West (Oregon) | us-west-2 | * usw2-az1 * usw2-az2 * usw2-az3 |
| Asia Pacific (Sydney) | ap-southeast-2 | * apse2-az1 * apse2-az2 * apse2-az3 |
| Asia Pacific (Mumbai) | ap-south-1 | * aps1-az1 * aps1-az2 * aps1-az3 |
| Asia Pacific (Singapore) | ap-southeast-1 | * apse1-az1 * apse1-az2 * apse1-az3 |
| Asia Pacific (Tokyo) | ap-northeast-1 | * apne1-az1 * apne1-az2 * apne1-az4 |
| Europe (Ireland) | eu-west-1 | * euw1-az1 * euw1-az2 * euw1-az3 |
| Europe (Frankfurt) | eu-central-1 | * euc1-az1 * euc1-az2 * euc1-az3 |

###### Important

Subnets must be located in the supported Availability Zones listed above. If you specify subnets in unsupported Availability Zones, the configuration will fail during resource creation.

To identify the Availability Zone ID of your subnets, you can use the following CLI command:

```
aws ec2 describe-subnets --subnet-ids subnet-12345678 --query 'Subnets[0].AvailabilityZoneId'
```

## IAM permissions

Amazon Bedrock AgentCore uses the service-linked role `AWSServiceRoleForBedrockAgentCoreNetwork`
to create and manage network interfaces in your VPC. This role is automatically created when you first
configure Amazon Bedrock AgentCore Runtime or AgentCore built-in tools to use VPC connectivity.

If you need to create this role manually, your IAM entity needs the following permissions:

```
{
    "Action": "iam:CreateServiceLinkedRole",
    "Effect": "Allow",
    "Resource": "arn:aws:iam::*:role/aws-service-role/network.bedrock-agentcore.amazonaws.com/AWSServiceRoleForBedrockAgentCoreNetwork",
    "Condition": {
        "StringLike": {
            "iam:AWSServiceName": "network.bedrock-agentcore.amazonaws.com"
        }
    }
}
```

This permission is already included in the AWS managed policy
[BedrockAgentCoreFullAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html "https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html").

## Best practices

For optimal performance and security with VPC-connected Amazon Bedrock AgentCore Runtime and built-in tools:

* **High Availability**:

  + Configure at least two private subnets in different Availability Zones. For a list of supported Availability
    Zones, see [Supported Availability Zones](#agentcore-supported-azs "#agentcore-supported-azs").
  + Deploy dependent resources (such as databases or caches) with multi-AZ support to avoid single points of failure.
* **Network Performance**:

  + Place Amazon Bedrock AgentCore Runtime or built-in tools subnets in the same Availability Zones as the resources they connect to. This reduces cross-AZ latency and data transfer costs.
  + Use VPC endpoints for AWS services whenever possible. Endpoints provide lower latency, higher reliability, and avoid NAT gateway charges for supported services.
* **Security**:

  + Apply the principle of least privilege when creating security group rules.
  + Enable VPC Flow Logs for auditing and monitoring. Review logs regularly to identify unexpected traffic patterns.
* **Internet Access**:

  + To provide internet access from Amazon Bedrock AgentCore Runtime or built-in tools inside a VPC, configure a NAT gateway in a public subnet. Update the route table for private subnets to send outbound traffic (0.0.0.0/0) to the NAT gateway.
  + We recommend using VPC endpoints for AWS services instead of internet routing to improve security and reduce costs.

## Configuring VPC access for runtime and tools

You can configure VPC access for Amazon Bedrock AgentCore Runtime and built-in tools using the AWS Management Console, AWS CLI, or AWS SDKs.

### Runtime configuration

AWS Management Console
:   1. Open the AgentCore console at [https://console.aws.amazon.com/bedrock-agentcore/home#](https://console.aws.amazon.com/bedrock-agentcore/home# "https://console.aws.amazon.com/bedrock-agentcore/home#").
    2. Navigate to the AgentCore section
    3. Select or create an Amazon Bedrock AgentCore Runtime configuration
    4. Choose your ECR image
    5. Under the Network configuration section, choose **VPC**
    6. Select your VPC from the dropdown list
    7. Select the appropriate subnets for your application needs
    8. Select one or more security groups to apply to the ENIs
    9. Save your configuration

AWS CLI
:   ```
    aws bedrock-agentcore create-runtime \
      --runtime-name "MyAgentRuntime" \
      --network-configuration '{
          "networkMode": "VPC",
          "networkModeConfig": {
            "subnets": ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
            "securityGroups": ["sg-0123456789abcdef0"]
          }
        }'
    ```

AWS SDK (Python)
:   ```
    import boto3

    client = boto3.client('bedrock-agentcore')

    response = client.create_runtime(
        runtimeName='MyAgentRuntime',
        networkConfiguration={
            'networkMode': 'VPC',
            'networkModeConfig': {
                'subnets': ['subnet-0123456789abcdef0', 'subnet-0123456789abcdef1'],
                'securityGroups': ['sg-0123456789abcdef0']
            }
        }
    )
    ```

### Code Interpreter configuration

AWS Management Console
:   1. Open the AgentCore console at [https://console.aws.amazon.com/bedrock-agentcore/home#](https://console.aws.amazon.com/bedrock-agentcore/home# "https://console.aws.amazon.com/bedrock-agentcore/home#").
    2. Navigate to AgentCore → Built-in Tools → Code Interpreter
    3. Select **Create Code Interpreter** or modify existing configuration
    4. Provide a tool name (optional)
    5. Configure execution role with necessary permissions
    6. Under Network configuration, choose **VPC**
    7. Select your VPC from the dropdown
    8. Choose appropriate subnets (recommend private subnets across multiple AZs with NAT gateway)
    9. Select security groups for ENI access control
    10. Configure execution role with necessary permissions
    11. Save your configuration

AWS CLI
:   ```
    aws bedrock-agentcore-control create-code-interpreter \
      --region <Region> \
      --name "my-code-interpreter" \
      --description "My Code Interpreter with VPC mode for data analysis" \
      --execution-role-arn "arn:aws:iam::123456789012:role/my-execution-role" \
      --network-configuration '{
        "networkMode": "VPC",
        "networkModeConfig": {
          "subnets": ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
          "securityGroups": ["sg-0123456789abcdef0"]
        }
      }'
    ```

AWS SDK (Python)
:   ```
    import boto3

    # Initialize the boto3 client
    cp_client = boto3.client(
        'bedrock-agentcore-control',
        region_name="<Region>",
        endpoint_url="https://bedrock-agentcore-control.<Region>.amazonaws.com"
    )

    # Create a Code Interpreter
    response = cp_client.create_code_interpreter(
        name="myTestVpcCodeInterpreter",
        description="Test code sandbox for development",
        executionRoleArn="arn:aws:iam::123456789012:role/my-execution-role",
        networkConfiguration={
            'networkMode': 'VPC',
            'networkModeConfig': {
                'subnets': ['subnet-0123456789abcdef0', 'subnet-0123456789abcdef1'],
                'securityGroups': ['sg-0123456789abcdef0']
            }
        }
    )

    # Print the Code Interpreter ID
    code_interpreter_id = response["codeInterpreterId"]
    print(f"Code Interpreter ID: {code_interpreter_id}")
    ```

### Browser Tool configuration

AWS Management Console
:   1. Open the AgentCore console at [https://console.aws.amazon.com/bedrock-agentcore/home#](https://console.aws.amazon.com/bedrock-agentcore/home# "https://console.aws.amazon.com/bedrock-agentcore/home#").
    2. In the navigation pane, choose **Built-in tools**
    3. Choose **Create Browser tool**
    4. Provide a tool name (optional) and description (optional)
    5. Set execution role permissions
    6. Under the Network configuration section, choose **VPC** mode
    7. Select your VPC and subnets
    8. Configure security groups for web access requirements
    9. Set execution role permissions
    10. Save your configuration

AWS CLI
:   ```
    aws bedrock-agentcore-control create-browser \
      --region <Region> \
      --name "my-browser" \
      --description "My browser for web interaction" \
      --network-configuration '{
        "networkMode": "VPC",
        "networkModeConfig": {
          "subnets": ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
          "securityGroups": ["sg-0123456789abcdef0"]
        }
      }' \
      --recording '{
        "enabled": true,
        "s3Location": {
          "bucket": "my-bucket-name",
          "prefix": "sessionreplay"
        }
      }' \
      --execution-role-arn "arn:aws:iam::123456789012:role/my-execution-role"
    ```

AWS SDK (Python)
:   ```
    import boto3

    # Initialize the boto3 client
    cp_client = boto3.client(
        'bedrock-agentcore-control',
        region_name="<Region>",
        endpoint_url="https://bedrock-agentcore-control.<Region>.amazonaws.com"
    )

    # Create a Browser
    response = cp_client.create_browser(
        name="myTestVpcBrowser",
        description="Test browser with VPC mode for development",
        networkConfiguration={
            'networkMode': 'VPC',
            'networkModeConfig': {
                'subnets': ['subnet-0123456789abcdef0', 'subnet-0123456789abcdef1'],
                'securityGroups': ['sg-0123456789abcdef0']
            }
        },
        executionRoleArn="arn:aws:iam::123456789012:role/Sessionreplay",
        recording={
            "enabled": True,
            "s3Location": {
                "bucket": "session-record-123456789012",
                "prefix": "replay-data"
            }
        }
    )
    ```

## Security group considerations

Security groups act as virtual firewalls for your Amazon Bedrock AgentCore Runtime or built-in tool when connected to a VPC. They control inbound and outbound traffic at the instance level. To configure security groups for your runtime:

* **Outbound rules** – Define outbound rules to allow your Amazon Bedrock AgentCore Runtime to connect to required VPC resources.
* **Inbound rules** – Ensure that the target resource's security group allows inbound connections from the security group associated with your Amazon Bedrock AgentCore Runtime.
* **Least privilege** – Apply the principle of least privilege by allowing only the minimum required traffic.

### Example: Connecting to an Amazon RDS database

When your Amazon Bedrock AgentCore Runtime connects to an Amazon RDS database, configure the security groups as follows:

###### Amazon Bedrock AgentCore Runtime security group

* **Outbound** – Allow TCP traffic to the RDS database's security group on port 3306 (MySQL).
* **Inbound** – Not required. The runtime only initiates outbound connections.

###### Amazon RDS database security group

* **Inbound** – Allow TCP traffic from the Amazon Bedrock AgentCore Runtime security group on port 3306.
* **Outbound** – Not required. Return traffic is automatically allowed because security groups are stateful.

## VPC endpoint configuration

When running Amazon Bedrock AgentCore Runtime in a private VPC without internet access, you must configure
the following VPC endpoints to ensure proper functionality:

### Required VPC endpoints

* **Amazon ECR Requirements**:

  + Docker endpoint: `com.amazonaws.region.ecr.dkr`
  + ECR API endpoint: `com.amazonaws.region.ecr.api`
* **Amazon S3 Requirements**:

  + Gateway endpoint for ECR docker layer storage: `com.amazonaws.region.s3`
* **CloudWatch Requirements**:

  + Logs endpoint: `com.amazonaws.region.logs`

###### Note

Be sure to replace `region` with your specific region if different.

### Internet access considerations

When you connect Amazon Bedrock AgentCore Runtime or a built-in tool to a Virtual Private Cloud (VPC), it does not have internet access by default. By default, these resources can communicate only with resources inside the same VPC. If your runtime or tool requires access to both VPC resources and the internet, you must configure your VPC accordingly.

#### Internet access architecture

To enable internet access for your VPC-connected Amazon Bedrock AgentCore Runtime or built-in tool, configure your VPC with the following components:

* **Private subnets** – Place the Amazon Bedrock AgentCore Runtime or tool's network interfaces in private subnets.
* **Public subnets with a NAT gateway** – Deploy a NAT gateway in one or more public subnets to provide outbound internet access for private resources.
* **Internet gateway (IGW)** – Attach an internet gateway to your VPC to enable communication between the NAT gateway and the internet.

#### Routing configuration

Update your subnet route tables as follows:

* **Private subnet route table** – Add a default route (0.0.0.0/0) that points to the NAT gateway. This allows outbound traffic from the runtime or tool to reach the internet.
* **Public subnet route table** – Add a default route (0.0.0.0/0) that points to the internet gateway. This allows the NAT gateway to communicate with the internet.

###### Important

Connecting Amazon Bedrock AgentCore Runtime and built-in tools to public subnets does not provide internet access.
Always use private subnets with NAT gateways for internet connectivity.

## Monitoring and troubleshooting

To monitor and troubleshoot your VPC-connected Amazon Bedrock AgentCore Runtime and tools:

### CloudWatch Logs

Enable CloudWatch Logs for your Amazon Bedrock AgentCore Runtime to identify any connectivity issues:

* Check error messages related to VPC connectivity
* Look for timeout errors when connecting to VPC resources
* Monitor initialization times (VPC connectivity may increase session startup times)

### Common issues and solutions

* **Connection timeouts**:

  + Verify security group rules are correct
  + Ensure route tables are properly configured
  + Check that the target resource is running and accepting connections
* **DNS resolution failures**:

  + Ensure that DNS resolution is enabled in your VPC
  + Verify that your DHCP options are configured correctly
* **Missing ENIs**:

  + Check the IAM permissions to ensure the service-linked role has appropriate permissions
  + Look for any service quotas that may have been reached

### Code Interpreter issues

* **Code Interpreter invoke call timeouts when trying to call a public endpoint**:

  + Verify that VPC is configured with NAT gateway for internet access
* **Invoke calls for a Code Interpreter with private VPC endpoints throw "AccessDenied" errors**:

  + Make sure the execution role passed during Code Interpreter creation has the right permissions for AWS service for which VPC endpoint was configured
* **Invoke calls for a Code Interpreter with some private VPC endpoints show "Unable to locate Credentials" error**:

  + Check that the execution role has been provided while creating the code interpreter

### Browser Tool issues

* **Live-View/Connection Stream is unable to load webpages and fails with connection timeouts**:

  + Check if the browser was created with Private Subnet with NAT Gateway

### Testing VPC connectivity

To verify that your Amazon Bedrock AgentCore Runtime and tools have proper VPC connectivity, you can test connections to your private resources and verify that network interfaces are created correctly in your specified subnets.

To verify that your Amazon Bedrock AgentCore tool has internet access, you can configure a Code Interpreter with your VPC configuration and use the `Invoke` API with `executeCommand` that attempts to connect to a public API or website using `curl` command and check the response. If the connection times out, review your VPC configuration, particularly your route tables and NAT gateway setup.

```
# Using awscurl
awscurl -X POST \
  "https://bedrock-agentcore.<Region>.amazonaws.com/code-interpreters/<code_interpreter_id>/tools/invoke" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "x-amzn-code-interpreter-session-id: your-session-id" \
  --service bedrock-agentcore \
  --region <Region> \
  -d '{
    "name": "executeCommand",
    "arguments": {
      "command": "curl amazon.com"
    }
  }'
```
