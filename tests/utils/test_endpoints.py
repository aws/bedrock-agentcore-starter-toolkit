import pytest

from bedrock_agentcore_starter_toolkit.utils.endpoints import (
    get_control_plane_endpoint,
    get_data_plane_endpoint,
)


class TestEndpoints:
    @pytest.mark.parametrize(
        "region,expected_endpoint",
        [
            ("us-west-2", "https://bedrock-agentcore.us-west-2.amazonaws.com"),
        ],
    )
    def test_get_data_plane_endpoint(self, region, expected_endpoint):
        assert get_data_plane_endpoint(region) == expected_endpoint

    @pytest.mark.parametrize(
        "region,expected_endpoint",
        [
            ("us-west-2", "https://bedrock-agentcore-control.us-west-2.amazonaws.com"),
        ],
    )
    def test_get_control_plane_endpoint(self, region, expected_endpoint):
        assert get_control_plane_endpoint(region) == expected_endpoint
