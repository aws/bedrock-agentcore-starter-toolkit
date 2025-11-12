# ---------------------------------------------------------------------------
# Both cdk and terraform tests will iterate through all scenarios
# Since only the IAC varies by scenario input, we only need to exercise each SDK at least once
# ---------------------------------------------------------------------------
from dataclasses import dataclass
from typing import Optional

from bedrock_agentcore_starter_toolkit.bootstrap.constants import SDKProvider


@dataclass(frozen=True)
class ScenarioConfig:
    sdk: Optional[SDKProvider]
    description: str


SCENARIOS: dict[str, ScenarioConfig] = {
    "scenario_0": ScenarioConfig(
        sdk=SDKProvider.STRANDS,
        description="custom auth; stm+ltm memory; custom headers",
    ),
    "scenario_1": ScenarioConfig(
        sdk=SDKProvider.OPENAI_AGENTS,
        description="default settings; stm memory",
    ),
    "scenario_2": ScenarioConfig(
        sdk=None,
        description="source provided; no sdk provider",
    ),
    "scenario_3": ScenarioConfig(
        sdk=SDKProvider.LANG_GRAPH,
        description="lang-graph run bootstrap as standalone",
    ),
}
