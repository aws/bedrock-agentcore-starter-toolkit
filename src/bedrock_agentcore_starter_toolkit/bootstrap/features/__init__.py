from .autogen.feature import AutogenFeature
from .googleadk.feature import GoogleADKFeature
from .langgraph.feature import LangGraphFeature
from .openaiagents.feature import OpenAIAgentsFeature
from .strands.feature import StrandsFeature
from .cdk.feature import CDKFeature
from .terraform.feature import TerraformFeature
from .types import BootstrapSDKProvider, BootstrapIACProvider, BootstrapFeature
from typing import Type
from .base_feature import Feature

feature_registry: dict[BootstrapFeature, Type[Feature]] = {
    BootstrapIACProvider.CDK: CDKFeature,
    BootstrapIACProvider.Terraform: TerraformFeature,
    BootstrapSDKProvider.Strands: StrandsFeature,
    BootstrapSDKProvider.LangGraph: LangGraphFeature,
    BootstrapSDKProvider.GoogleADK: GoogleADKFeature,
    BootstrapSDKProvider.OpenAIAgents: OpenAIAgentsFeature,
    BootstrapSDKProvider.Autogen: AutogenFeature
}