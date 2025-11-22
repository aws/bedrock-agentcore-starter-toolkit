"""Implements code generation for supported SDK and IaC providers."""

from typing import Type

from ..constants import IACProvider, SDKProvider
from ..types import CreateIACProvider, CreateSDKProvider
from .autogen.feature import AutogenFeature
from .base_feature import Feature
from .cdk.feature import CDKFeature
from .crewai.feature import CrewAIFeature
from .googleadk.feature import GoogleADKFeature
from .langchain.feature import LangChainFeature
from .openaiagents.feature import OpenAIAgentsFeature
from .strands.feature import StrandsFeature
from .terraform.feature import TerraformFeature

sdk_feature_registry: dict[CreateSDKProvider, Type[Feature]] = {
    SDKProvider.STRANDS: StrandsFeature,
    SDKProvider.LANG_CHAIN: LangChainFeature,
    SDKProvider.GOOGLE_ADK: GoogleADKFeature,
    SDKProvider.OPENAI_AGENTS: OpenAIAgentsFeature,
    SDKProvider.CREWAI: CrewAIFeature,
    SDKProvider.AUTOGEN: AutogenFeature,
}

iac_feature_registry: dict[CreateIACProvider, Type[Feature]] = {
    IACProvider.CDK: CDKFeature,
    IACProvider.TERRAFORM: TerraformFeature,
}
