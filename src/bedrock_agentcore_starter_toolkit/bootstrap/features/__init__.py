"""Implements code generation for supported SDK and IaC providers."""

from typing import Type

from ..constants import IACProvider, SDKProvider
from ..types import BootstrapIACProvider, BootstrapSDKProvider
from .autogen.feature import AutogenFeature
from .base_feature import Feature
from .cdk.feature import CDKFeature
from .crewai.feature import CrewAIFeature
from .googleadk.feature import GoogleADKFeature
from .langgraph.feature import LangGraphFeature
from .openaiagents.feature import OpenAIAgentsFeature
from .strands.feature import StrandsFeature
from .terraform.feature import TerraformFeature

sdk_feature_registry: dict[BootstrapSDKProvider, Type[Feature]] = {
    SDKProvider.STRANDS: StrandsFeature,
    SDKProvider.LANG_GRAPH: LangGraphFeature,
    SDKProvider.GOOGLE_ADK: GoogleADKFeature,
    SDKProvider.OPENAI_AGENTS: OpenAIAgentsFeature,
    SDKProvider.CREWAI: CrewAIFeature,
    SDKProvider.AUTOGEN: AutogenFeature,
}

iac_feature_registry: dict[BootstrapIACProvider, Type[Feature]] = {
    IACProvider.CDK: CDKFeature,
    IACProvider.TERRAFORM: TerraformFeature,
}
