from .autogen.feature import AutogenFeature
from .crewai.feature import CrewAIFeature
from .googleadk.feature import GoogleADKFeature
from .langgraph.feature import LangGraphFeature
from .openaiagents.feature import OpenAIAgentsFeature
from .strands.feature import StrandsFeature
from .cdk.feature import CDKFeature
from .terraform.feature import TerraformFeature
from .types import BootstrapSDKProvider, BootstrapIACProvider
from typing import Type
from .base_feature import Feature

sdk_feature_registry: dict[BootstrapSDKProvider, Type[Feature]] = {
    BootstrapSDKProvider.Strands: StrandsFeature,
    BootstrapSDKProvider.LangGraph: LangGraphFeature,
    BootstrapSDKProvider.GoogleADK: GoogleADKFeature,
    BootstrapSDKProvider.OpenAIAgents: OpenAIAgentsFeature,
    BootstrapSDKProvider.CrewAI: CrewAIFeature,
    BootstrapSDKProvider.Autogen: AutogenFeature,
}

iac_feature_registry: dict[BootstrapIACProvider, Type[Feature]] = {
    BootstrapIACProvider.CDK: CDKFeature,
    BootstrapIACProvider.Terraform: TerraformFeature
}