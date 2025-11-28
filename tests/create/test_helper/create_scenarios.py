# ---------------------------------------------------------------------------
# Both cdk and terraform tests will iterate through all scenarios
# Since only the IAC varies by scenario input, we only need to exercise each SDK at least once
# ---------------------------------------------------------------------------
from dataclasses import dataclass

from bedrock_agentcore_starter_toolkit.create.constants import ModelProvider, SDKProvider


@dataclass(frozen=True)
class ScenarioConfig:
    sdk: SDKProvider
    modelProvider: ModelProvider
    description: str


IAC_WITH_CONFIG_SCENARIOS: dict[str, ScenarioConfig] = {
    "scenario_0": ScenarioConfig(
        sdk=SDKProvider.STRANDS,
        modelProvider=ModelProvider.Bedrock,
        description="custom auth; stm+ltm memory; custom headers",
    ),
    "scenario_1": ScenarioConfig(
        sdk=SDKProvider.OPENAI_AGENTS,
        modelProvider=ModelProvider.OpenAI,
        description="default settings; stm memory",
    ),
}
