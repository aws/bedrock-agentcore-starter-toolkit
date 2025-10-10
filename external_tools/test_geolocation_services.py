"""
Unit tests for Geolocation and Risk Assessment Services.
"""

import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from external_tools.geolocation_services import (
    GeolocationTool, GeographicLocation, LocationRiskAssessment, TravelAnalysis,
    LocationRiskLevel, LocationVerificationStatus, TravelPattern,
    create_geolocation_tool
)
from external_tools.tool_integrator import ToolConfiguration, ToolType


@pytest.fixture
def geolocation_config():
    """Create test configuration for geolocation tool."""
    return ToolConfiguration(
        tool_id="test_geolocation",
        tool_name="Test Geolocation Service",
        tool_type=ToolType.GEOLOCATION,
        base_url="https://api.test-geolocation.com",
        api_key="test_api_key",
        timeout_seconds=15,
        rate_limit_per_minute=100,
        custom_parameters={
            "provider": "generic",
            "enable_risk_assessment": True,
            "max_travel_velocity": 1000,
            "risk_threshold": 0.7
        }
    )


@pytest.fixture
def geolocation_tool(geolocation_config):
    """Create geolocation tool for testing."""
    return GeolocationTool(geolocation_config)


@pytest.fixture
def sample_location():
    """Create sample geographic location for testing."""
    return GeographicLocation(
        latitude=40.7128,
        longitude=-74.0060,
        country="United States",
        country_code="US",
        city="New York",
        region="New York",
        timezone="America/New_York",
        ip_address="192.168.1.100",
        accuracy_radius=100,
        is_vpn=False,
        is_proxy=False,
        is_tor=False
    )


@pytest.fixture
def sample_vpn_location():
    """Create sample VPN location for testing."""
    return GeographicLocation(
        latitude=51.5074,
        longitude=-0.1278,
        country="United Kingdom",
        country_code="GB",
        city="London",
        region="England",
        timezone="Europe/London",
        ip_address="203.0.113.45",
        accuracy_radius=50,
        is_vpn=True,
        is_proxy=False,
        is_tor=False
    )


class TestGeolocationTool:
    """Test cases for GeolocationTool."""
    
    def test_tool_initialization(self, geolocation_tool):
        """Test that geolocation tool initializes correctly."""
        assert geolocation_tool.config.tool_name == "Test Geolocation Service"
        assert geolocation_tool.config.tool_type == ToolType.GEOLOCATION
        assert geolocation_tool.provider == "generic"
        assert geolocation_tool.enable_risk_assessment is True
        assert geolocation_tool.max_travel_velocity == 1000
        assert geolocation_tool.risk_threshold == 0.7
    
    def test_geolocate_ip_success(self, geolocation_tool):
        """Test successful IP geolocation."""
        with patch.object(geolocation_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "location": {
                        "latitude": 37.7749,
                        "longitude": -122.4194,
                        "country": "United States",
                        "country_code": "US",
                        "city": "San Francisco",
                        "region": "California",
                        "timezone": "America/Los_Angeles",
                        "ip_address": "8.8.8.8",
                        "accuracy_radius": 100,
                        "is_vpn": False,
                        "is_proxy": False,
                        "is_tor": False
                    }
                },
                response_time_ms=100.0,
                tool_id="test_geolocation",
                timestamp=datetime.now()
            )
            
            location = geolocation_tool.geolocate_ip("8.8.8.8")
            
            assert isinstance(location, GeographicLocation)
            assert location.latitude == 37.7749
            assert location.longitude == -122.4194
            assert location.country == "United States"
            assert location.city == "San Francisco"
            assert location.ip_address == "8.8.8.8"
            assert location.is_vpn is False
    
    def test_geolocate_ip_failure(self, geolocation_tool):
        """Test failed IP geolocation."""
        with patch.object(geolocation_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=False,
                data={},
                error_message="Invalid IP address",
                response_time_ms=50.0,
                tool_id="test_geolocation",
                timestamp=datetime.now()
            )
            
            location = geolocation_tool.geolocate_ip("invalid_ip")
            
            assert location is None
    
    def test_assess_location_risk_low_risk(self, geolocation_tool, sample_location):
        """Test location risk assessment for low-risk location."""
        with patch.object(geolocation_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "risk_assessment": {
                        "risk_level": "low",
                        "risk_score": 0.2,
                        "risk_factors": [],
                        "verification_status": "verified",
                        "confidence_score": 0.9,
                        "recommendations": ["Standard processing acceptable"]
                    }
                },
                response_time_ms=120.0,
                tool_id="test_geolocation",
                timestamp=datetime.now()
            )
            
            assessment = geolocation_tool.assess_location_risk(sample_location)
            
            assert isinstance(assessment, LocationRiskAssessment)
            assert assessment.risk_level == LocationRiskLevel.LOW
            assert assessment.risk_score == 0.2
            assert assessment.verification_status == LocationVerificationStatus.VERIFIED
            assert assessment.confidence_score == 0.9
            assert len(assessment.risk_factors) == 0
    
    def test_assess_location_risk_high_risk(self, geolocation_tool, sample_vpn_location):
        """Test location risk assessment for high-risk location."""
        with patch.object(geolocation_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "risk_assessment": {
                        "risk_level": "high",
                        "risk_score": 0.8,
                        "risk_factors": ["VPN/Proxy detected", "Identity concealment"],
                        "verification_status": "suspicious",
                        "confidence_score": 0.7,
                        "recommendations": ["Require additional verification", "Consider manual review"]
                    }
                },
                response_time_ms=150.0,
                tool_id="test_geolocation",
                timestamp=datetime.now()
            )
            
            assessment = geolocation_tool.assess_location_risk(sample_vpn_location)
            
            assert assessment.risk_level == LocationRiskLevel.HIGH
            assert assessment.risk_score == 0.8
            assert assessment.verification_status == LocationVerificationStatus.SUSPICIOUS
            assert len(assessment.risk_factors) > 0
            assert "VPN/Proxy detected" in assessment.risk_factors
    
    def test_assess_location_risk_disabled(self, geolocation_config):
        """Test location risk assessment when disabled."""
        geolocation_config.custom_parameters["enable_risk_assessment"] = False
        tool = GeolocationTool(geolocation_config)
        
        location = GeographicLocation(
            latitude=40.7128, longitude=-74.0060,
            country="US", country_code="US", city="New York"
        )
        
        assessment = tool.assess_location_risk(location)
        
        assert assessment.risk_level == LocationRiskLevel.MEDIUM
        assert assessment.risk_score == 0.5
        assert assessment.verification_status == LocationVerificationStatus.UNKNOWN
        assert "Risk assessment disabled" in assessment.risk_factors
    
    def test_analyze_travel_pattern_normal(self, geolocation_tool):
        """Test travel pattern analysis for normal travel."""
        current_location = GeographicLocation(
            latitude=40.7128, longitude=-74.0060,  # New York
            country="US", country_code="US", city="New York"
        )
        
        previous_location = GeographicLocation(
            latitude=40.6892, longitude=-74.0445,  # Jersey City (nearby)
            country="US", country_code="US", city="Jersey City"
        )
        
        time_difference = timedelta(hours=2)
        
        analysis = geolocation_tool.analyze_travel_pattern(
            "user_123", current_location, previous_location, time_difference
        )
        
        assert isinstance(analysis, TravelAnalysis)
        assert analysis.user_id == "user_123"
        assert analysis.travel_pattern == TravelPattern.NORMAL
        assert analysis.is_possible_travel is True
        assert analysis.distance_km < 50  # Short distance
        assert analysis.travel_velocity_kmh < 100  # Reasonable speed
    
    def test_analyze_travel_pattern_impossible(self, geolocation_tool):
        """Test travel pattern analysis for impossible travel."""
        current_location = GeographicLocation(
            latitude=40.7128, longitude=-74.0060,  # New York
            country="US", country_code="US", city="New York"
        )
        
        previous_location = GeographicLocation(
            latitude=34.0522, longitude=-118.2437,  # Los Angeles
            country="US", country_code="US", city="Los Angeles"
        )
        
        time_difference = timedelta(minutes=30)  # Too short for cross-country travel
        
        analysis = geolocation_tool.analyze_travel_pattern(
            "user_456", current_location, previous_location, time_difference
        )
        
        assert analysis.travel_pattern == TravelPattern.IMPOSSIBLE_TRAVEL
        assert analysis.is_possible_travel is False
        assert analysis.travel_velocity_kmh > 1000
        assert len(analysis.risk_indicators) > 0
        assert "Impossible travel speed" in analysis.risk_indicators[0]
    
    def test_analyze_travel_pattern_no_previous_location(self, geolocation_tool):
        """Test travel pattern analysis with no previous location."""
        current_location = GeographicLocation(
            latitude=40.7128, longitude=-74.0060,
            country="US", country_code="US", city="New York"
        )
        
        analysis = geolocation_tool.analyze_travel_pattern("user_789", current_location)
        
        assert analysis.travel_pattern == TravelPattern.NORMAL
        assert analysis.is_possible_travel is True
        assert analysis.distance_km == 0.0
        assert analysis.travel_velocity_kmh == 0.0
        assert len(analysis.risk_indicators) == 0
    
    def test_verify_location_consistency_consistent(self, geolocation_tool):
        """Test location consistency verification for consistent locations."""
        claimed_location = GeographicLocation(
            latitude=40.7128, longitude=-74.0060,  # New York
            country="US", country_code="US", city="New York"
        )
        
        detected_location = GeographicLocation(
            latitude=40.7589, longitude=-73.9851,  # Manhattan (nearby)
            country="US", country_code="US", city="New York"
        )
        
        result = geolocation_tool.verify_location_consistency(
            claimed_location, detected_location, tolerance_km=50.0
        )
        
        assert result["is_consistent"] is True
        assert result["distance_km"] < 50.0
        assert result["verification_status"] == "verified"
        assert result["risk_level"] == "low"
    
    def test_verify_location_consistency_inconsistent(self, geolocation_tool):
        """Test location consistency verification for inconsistent locations."""
        claimed_location = GeographicLocation(
            latitude=40.7128, longitude=-74.0060,  # New York
            country="US", country_code="US", city="New York"
        )
        
        detected_location = GeographicLocation(
            latitude=34.0522, longitude=-118.2437,  # Los Angeles
            country="US", country_code="US", city="Los Angeles"
        )
        
        result = geolocation_tool.verify_location_consistency(
            claimed_location, detected_location, tolerance_km=50.0
        )
        
        assert result["is_consistent"] is False
        assert result["distance_km"] > 1000.0  # Cross-country distance
        assert result["verification_status"] == "failed"
        assert result["risk_level"] == "high"
        assert "risk_factors" in result
        assert len(result["risk_factors"]) > 0
    
    def test_get_high_risk_regions_success(self, geolocation_tool):
        """Test successful retrieval of high-risk regions."""
        with patch.object(geolocation_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "risk_regions": [
                        {
                            "country": "Anonymous Proxy",
                            "country_code": "A1",
                            "risk_level": "very_high",
                            "risk_factors": ["Anonymous proxy", "Identity concealment"]
                        },
                        {
                            "country": "Tor Network",
                            "country_code": "T1",
                            "risk_level": "very_high",
                            "risk_factors": ["Tor network", "Anonymization service"]
                        }
                    ]
                },
                response_time_ms=80.0,
                tool_id="test_geolocation",
                timestamp=datetime.now()
            )
            
            regions = geolocation_tool.get_high_risk_regions()
            
            assert len(regions) == 2
            assert regions[0]["country"] == "Anonymous Proxy"
            assert regions[0]["risk_level"] == "very_high"
            assert regions[1]["country"] == "Tor Network"
    
    def test_mock_geolocation_private_ip(self, geolocation_tool):
        """Test mock geolocation for private IP addresses."""
        result = geolocation_tool._mock_geolocation({"ip_address": "192.168.1.100"})
        
        location_data = result["location"]
        assert location_data["country"] == "United States"
        assert location_data["city"] == "New York"
        assert location_data["is_vpn"] is False
        assert location_data["ip_address"] == "192.168.1.100"
    
    def test_mock_geolocation_vpn_detection(self, geolocation_tool):
        """Test mock geolocation VPN detection."""
        result = geolocation_tool._mock_geolocation({"ip_address": "203.0.113.45"})
        
        location_data = result["location"]
        assert location_data["country"] == "United Kingdom"
        assert location_data["city"] == "London"
        assert location_data["is_vpn"] is True
    
    def test_mock_risk_assessment_low_risk(self, geolocation_tool):
        """Test mock risk assessment for low-risk location."""
        location_data = {
            "country": "United States",
            "is_vpn": False
        }
        
        result = geolocation_tool._mock_risk_assessment({"location": location_data})
        
        risk_data = result["risk_assessment"]
        assert risk_data["risk_level"] in ["very_low", "low"]
        assert risk_data["risk_score"] < 0.5
        assert risk_data["verification_status"] == "verified"
    
    def test_mock_risk_assessment_high_risk(self, geolocation_tool):
        """Test mock risk assessment for high-risk location."""
        location_data = {
            "country": "Unknown",
            "is_vpn": True
        }
        
        result = geolocation_tool._mock_risk_assessment({"location": location_data})
        
        risk_data = result["risk_assessment"]
        assert risk_data["risk_level"] in ["high", "very_high"]
        assert risk_data["risk_score"] >= 0.5
        assert "VPN/Proxy detected" in risk_data["risk_factors"]
        assert "High-risk country" in risk_data["risk_factors"]
    
    def test_calculate_distance(self, geolocation_tool):
        """Test distance calculation between geographic points."""
        # New York to Los Angeles (approximately 3944 km)
        distance = geolocation_tool._calculate_distance(
            40.7128, -74.0060,  # New York
            34.0522, -118.2437  # Los Angeles
        )
        
        # Should be approximately 3944 km (allow 10% tolerance)
        expected_distance = 3944
        assert abs(distance - expected_distance) < (expected_distance * 0.1)
    
    def test_calculate_distance_same_location(self, geolocation_tool):
        """Test distance calculation for same location."""
        distance = geolocation_tool._calculate_distance(
            40.7128, -74.0060,  # New York
            40.7128, -74.0060   # Same location
        )
        
        assert distance == 0.0
    
    def test_analyze_travel_velocity_patterns(self, geolocation_tool):
        """Test travel velocity pattern analysis."""
        # Test impossible travel
        pattern, indicators = geolocation_tool._analyze_travel_velocity(4000, 2, 2000)
        assert pattern == TravelPattern.IMPOSSIBLE_TRAVEL
        assert len(indicators) > 0
        
        # Test high velocity (air travel) - distance > 1000km
        pattern, indicators = geolocation_tool._analyze_travel_velocity(2000, 4, 500)
        assert pattern == TravelPattern.FREQUENT_TRAVELER
        
        # Test location hopping
        pattern, indicators = geolocation_tool._analyze_travel_velocity(100, 0.5, 200)
        assert pattern == TravelPattern.LOCATION_HOPPING
        
        # Test normal travel
        pattern, indicators = geolocation_tool._analyze_travel_velocity(50, 2, 25)
        assert pattern == TravelPattern.NORMAL


class TestGeographicLocation:
    """Test cases for GeographicLocation dataclass."""
    
    def test_geographic_location_creation(self):
        """Test creating GeographicLocation with all fields."""
        location = GeographicLocation(
            latitude=37.7749,
            longitude=-122.4194,
            country="United States",
            country_code="US",
            city="San Francisco",
            region="California",
            postal_code="94102",
            timezone="America/Los_Angeles",
            ip_address="8.8.8.8",
            accuracy_radius=100,
            is_vpn=False,
            is_proxy=False,
            is_tor=False
        )
        
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.country == "United States"
        assert location.city == "San Francisco"
        assert location.is_vpn is False
    
    def test_geographic_location_minimal(self):
        """Test creating GeographicLocation with minimal required fields."""
        location = GeographicLocation(
            latitude=40.7128,
            longitude=-74.0060,
            country="US",
            country_code="US",
            city="New York"
        )
        
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.region is None
        assert location.postal_code is None


class TestLocationRiskAssessment:
    """Test cases for LocationRiskAssessment dataclass."""
    
    def test_location_risk_assessment_creation(self, sample_location):
        """Test creating LocationRiskAssessment."""
        assessment = LocationRiskAssessment(
            location=sample_location,
            risk_level=LocationRiskLevel.MEDIUM,
            risk_score=0.5,
            risk_factors=["Unknown user pattern"],
            verification_status=LocationVerificationStatus.VERIFIED,
            confidence_score=0.8,
            assessment_timestamp=datetime.now(),
            recommendations=["Monitor for unusual activity"]
        )
        
        assert assessment.location == sample_location
        assert assessment.risk_level == LocationRiskLevel.MEDIUM
        assert assessment.risk_score == 0.5
        assert len(assessment.risk_factors) == 1
        assert assessment.verification_status == LocationVerificationStatus.VERIFIED


class TestTravelAnalysis:
    """Test cases for TravelAnalysis dataclass."""
    
    def test_travel_analysis_creation(self, sample_location):
        """Test creating TravelAnalysis."""
        analysis = TravelAnalysis(
            user_id="user_123",
            current_location=sample_location,
            previous_location=None,
            distance_km=0.0,
            time_difference_hours=0.0,
            travel_velocity_kmh=0.0,
            travel_pattern=TravelPattern.NORMAL,
            is_possible_travel=True,
            risk_indicators=[],
            analysis_timestamp=datetime.now()
        )
        
        assert analysis.user_id == "user_123"
        assert analysis.current_location == sample_location
        assert analysis.travel_pattern == TravelPattern.NORMAL
        assert analysis.is_possible_travel is True


class TestCreateGeolocationTool:
    """Test cases for the factory function."""
    
    def test_create_generic_tool(self):
        """Test creating generic geolocation tool."""
        tool = create_geolocation_tool(
            tool_id="test_generic",
            provider="generic"
        )
        
        assert tool.config.tool_id == "test_generic"
        assert tool.provider == "generic"
        assert "mock-geolocation" in tool.config.base_url
    
    def test_create_maxmind_tool(self):
        """Test creating MaxMind geolocation tool."""
        tool = create_geolocation_tool(
            tool_id="test_maxmind",
            provider="maxmind",
            api_key="maxmind_api_key"
        )
        
        assert tool.config.tool_id == "test_maxmind"
        assert tool.provider == "maxmind"
        assert tool.config.api_key == "maxmind_api_key"
        assert "maxmind.com" in tool.config.base_url
    
    def test_create_ipinfo_tool(self):
        """Test creating IPInfo geolocation tool."""
        tool = create_geolocation_tool(
            tool_id="test_ipinfo",
            provider="ipinfo",
            api_key="ipinfo_token"
        )
        
        assert tool.config.tool_id == "test_ipinfo"
        assert tool.provider == "ipinfo"
        assert "ipinfo.io" in tool.config.base_url
    
    def test_create_with_custom_base_url(self):
        """Test creating tool with custom base URL."""
        custom_url = "https://custom-geolocation-api.com"
        tool = create_geolocation_tool(
            tool_id="test_custom",
            provider="generic",
            base_url=custom_url
        )
        
        assert tool.config.base_url == custom_url


if __name__ == "__main__":
    pytest.main([__file__])