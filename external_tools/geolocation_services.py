"""
Geolocation and Risk Assessment Services

Provides integration with geolocation APIs for location verification,
risk assessment, and geographic fraud detection.
"""

import logging
import time
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .tool_integrator import ExternalTool, ToolConfiguration, ToolResponse, ToolType

logger = logging.getLogger(__name__)


class LocationRiskLevel(Enum):
    """Risk levels for geographic locations."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    BLOCKED = "blocked"


class LocationVerificationStatus(Enum):
    """Status of location verification."""
    VERIFIED = "verified"
    FAILED = "failed"
    SUSPICIOUS = "suspicious"
    UNKNOWN = "unknown"
    BLOCKED_REGION = "blocked_region"


class TravelPattern(Enum):
    """Travel pattern classifications."""
    NORMAL = "normal"
    FREQUENT_TRAVELER = "frequent_traveler"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    SUSPICIOUS_VELOCITY = "suspicious_velocity"
    LOCATION_HOPPING = "location_hopping"


@dataclass
class GeographicLocation:
    """Geographic location information."""
    latitude: float
    longitude: float
    country: str
    country_code: str
    city: str
    region: Optional[str] = None
    postal_code: Optional[str] = None
    timezone: Optional[str] = None
    ip_address: Optional[str] = None
    accuracy_radius: Optional[int] = None
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False


@dataclass
class LocationRiskAssessment:
    """Risk assessment for a geographic location."""
    location: GeographicLocation
    risk_level: LocationRiskLevel
    risk_score: float
    risk_factors: List[str]
    verification_status: LocationVerificationStatus
    confidence_score: float
    assessment_timestamp: datetime
    risk_details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TravelAnalysis:
    """Analysis of travel patterns and velocity."""
    user_id: str
    current_location: GeographicLocation
    previous_location: Optional[GeographicLocation]
    distance_km: float
    time_difference_hours: float
    travel_velocity_kmh: float
    travel_pattern: TravelPattern
    is_possible_travel: bool
    risk_indicators: List[str]
    analysis_timestamp: datetime


@dataclass
class LocationHistory:
    """Historical location data for a user."""
    user_id: str
    locations: List[Tuple[GeographicLocation, datetime]]
    common_locations: List[GeographicLocation]
    travel_patterns: List[TravelPattern]
    risk_events: List[Dict[str, Any]]
    last_updated: datetime


class GeolocationTool(ExternalTool):
    """
    Geolocation and risk assessment tool integration.
    
    Provides capabilities for:
    - IP geolocation and verification
    - Location-based risk assessment
    - Travel pattern analysis
    - Geographic fraud detection
    """
    
    def __init__(self, config: ToolConfiguration):
        """Initialize geolocation tool."""
        super().__init__(config)
        self.provider = config.custom_parameters.get("provider", "generic")
        self.enable_risk_assessment = config.custom_parameters.get("enable_risk_assessment", True)
        self.max_travel_velocity = config.custom_parameters.get("max_travel_velocity", 1000)  # km/h
        self.risk_threshold = config.custom_parameters.get("risk_threshold", 0.7)
        
        logger.info(f"Initialized geolocation tool with provider: {self.provider}")
    
    def call_api(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make API call to geolocation service."""
        start_time = time.time()
        
        try:
            # Check rate limit
            if not self._check_rate_limit():
                return ToolResponse(
                    success=False,
                    data={},
                    response_time_ms=0.0,
                    tool_id=self.config.tool_id,
                    timestamp=datetime.now(),
                    error_message="Rate limit exceeded"
                )
            
            # Check cache
            cache_key = self._get_cache_key(endpoint, data)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
            
            # Make actual API call
            response = self._make_request(endpoint, data)
            
            # Update metrics
            self._update_metrics(response)
            
            # Cache successful responses
            if response.success:
                self._cache_response(cache_key, response)
            
            return response
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_response = ToolResponse(
                success=False,
                data={},
                response_time_ms=response_time_ms,
                tool_id=self.config.tool_id,
                timestamp=datetime.now(),
                error_message=str(e)
            )
            self._update_metrics(error_response)
            return error_response
    
    def geolocate_ip(self, ip_address: str) -> Optional[GeographicLocation]:
        """
        Get geographic location for an IP address.
        
        Args:
            ip_address: IP address to geolocate
            
        Returns:
            GeographicLocation object or None if failed
        """
        request_data = {"ip_address": ip_address}
        response = self.call_api("geolocate", request_data)
        
        if response.success:
            return self._parse_location_response(response.data)
        else:
            logger.error(f"Failed to geolocate IP {ip_address}: {response.error_message}")
            return None
    
    def assess_location_risk(
        self, 
        location: GeographicLocation,
        user_context: Optional[Dict[str, Any]] = None
    ) -> LocationRiskAssessment:
        """
        Assess risk for a geographic location.
        
        Args:
            location: Geographic location to assess
            user_context: Additional user context for risk assessment
            
        Returns:
            LocationRiskAssessment with risk details
        """
        if not self.enable_risk_assessment:
            return LocationRiskAssessment(
                location=location,
                risk_level=LocationRiskLevel.MEDIUM,
                risk_score=0.5,
                risk_factors=["Risk assessment disabled"],
                verification_status=LocationVerificationStatus.UNKNOWN,
                confidence_score=0.0,
                assessment_timestamp=datetime.now(),
                recommendations=["Enable risk assessment for detailed analysis"]
            )
        
        request_data = {
            "location": {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "country": location.country,
                "city": location.city,
                "ip_address": location.ip_address
            },
            "user_context": user_context or {}
        }
        
        response = self.call_api("assess_risk", request_data)
        
        if response.success:
            return self._parse_risk_assessment(response.data, location)
        else:
            # Return default medium risk assessment
            return LocationRiskAssessment(
                location=location,
                risk_level=LocationRiskLevel.MEDIUM,
                risk_score=0.5,
                risk_factors=[f"Assessment failed: {response.error_message}"],
                verification_status=LocationVerificationStatus.FAILED,
                confidence_score=0.0,
                assessment_timestamp=datetime.now(),
                recommendations=["Retry risk assessment", "Use alternative verification"]
            )
    
    def analyze_travel_pattern(
        self,
        user_id: str,
        current_location: GeographicLocation,
        previous_location: Optional[GeographicLocation] = None,
        time_difference: Optional[timedelta] = None
    ) -> TravelAnalysis:
        """
        Analyze travel patterns for fraud detection.
        
        Args:
            user_id: User identifier
            current_location: Current geographic location
            previous_location: Previous known location
            time_difference: Time between locations
            
        Returns:
            TravelAnalysis with pattern assessment
        """
        if not previous_location or not time_difference:
            # No previous location data for comparison
            return TravelAnalysis(
                user_id=user_id,
                current_location=current_location,
                previous_location=previous_location,
                distance_km=0.0,
                time_difference_hours=0.0,
                travel_velocity_kmh=0.0,
                travel_pattern=TravelPattern.NORMAL,
                is_possible_travel=True,
                risk_indicators=[],
                analysis_timestamp=datetime.now()
            )
        
        # Calculate distance and velocity
        distance_km = self._calculate_distance(
            previous_location.latitude, previous_location.longitude,
            current_location.latitude, current_location.longitude
        )
        
        time_hours = time_difference.total_seconds() / 3600
        velocity_kmh = distance_km / time_hours if time_hours > 0 else float('inf')
        
        # Analyze travel pattern
        travel_pattern, risk_indicators = self._analyze_travel_velocity(
            distance_km, time_hours, velocity_kmh
        )
        
        is_possible = velocity_kmh <= self.max_travel_velocity
        
        return TravelAnalysis(
            user_id=user_id,
            current_location=current_location,
            previous_location=previous_location,
            distance_km=distance_km,
            time_difference_hours=time_hours,
            travel_velocity_kmh=velocity_kmh,
            travel_pattern=travel_pattern,
            is_possible_travel=is_possible,
            risk_indicators=risk_indicators,
            analysis_timestamp=datetime.now()
        )
    
    def verify_location_consistency(
        self,
        claimed_location: GeographicLocation,
        detected_location: GeographicLocation,
        tolerance_km: float = 50.0
    ) -> Dict[str, Any]:
        """
        Verify consistency between claimed and detected locations.
        
        Args:
            claimed_location: Location claimed by user
            detected_location: Location detected from IP/device
            tolerance_km: Acceptable distance tolerance in kilometers
            
        Returns:
            Dictionary with verification results
        """
        distance_km = self._calculate_distance(
            claimed_location.latitude, claimed_location.longitude,
            detected_location.latitude, detected_location.longitude
        )
        
        is_consistent = distance_km <= tolerance_km
        
        verification_result = {
            "is_consistent": is_consistent,
            "distance_km": distance_km,
            "tolerance_km": tolerance_km,
            "claimed_location": {
                "country": claimed_location.country,
                "city": claimed_location.city,
                "coordinates": f"{claimed_location.latitude}, {claimed_location.longitude}"
            },
            "detected_location": {
                "country": detected_location.country,
                "city": detected_location.city,
                "coordinates": f"{detected_location.latitude}, {detected_location.longitude}"
            },
            "verification_status": LocationVerificationStatus.VERIFIED.value if is_consistent else LocationVerificationStatus.FAILED.value,
            "risk_level": LocationRiskLevel.LOW.value if is_consistent else LocationRiskLevel.HIGH.value
        }
        
        if not is_consistent:
            verification_result["risk_factors"] = [
                f"Location mismatch: {distance_km:.1f}km apart",
                "Potential location spoofing",
                "Geographic inconsistency detected"
            ]
        
        return verification_result
    
    def get_high_risk_regions(self) -> List[Dict[str, Any]]:
        """
        Get list of high-risk geographic regions.
        
        Returns:
            List of high-risk regions with details
        """
        response = self.call_api("get_risk_regions", {})
        
        if response.success:
            return response.data.get("risk_regions", [])
        else:
            # Return default high-risk regions
            return [
                {
                    "country": "Unknown",
                    "country_code": "XX",
                    "risk_level": "high",
                    "risk_factors": ["Unidentified location", "Potential anonymization"]
                }
            ]
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make HTTP request to geolocation service."""
        start_time = time.time()
        
        try:
            url = f"{self.config.base_url}/{endpoint}"
            
            # Prepare request based on provider
            if self.provider == "maxmind":
                response_data = self._call_maxmind_api(url, data)
            elif self.provider == "ipinfo":
                response_data = self._call_ipinfo_api(url, data)
            elif self.provider == "ipgeolocation":
                response_data = self._call_ipgeolocation_api(url, data)
            else:
                # Generic/mock implementation
                response_data = self._call_generic_api(url, data, endpoint)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return ToolResponse(
                success=True,
                data=response_data,
                response_time_ms=response_time_ms,
                tool_id=self.config.tool_id,
                timestamp=datetime.now(),
                status_code=200
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return ToolResponse(
                success=False,
                data={},
                response_time_ms=response_time_ms,
                tool_id=self.config.tool_id,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    def _call_maxmind_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call MaxMind GeoIP API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.config.api_key}"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_ipinfo_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call IPInfo API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_ipgeolocation_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call IP Geolocation API."""
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key to data for this provider
        data["apiKey"] = self.config.api_key
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_generic_api(self, url: str, data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Generic/mock geolocation implementation."""
        # Simulate processing time
        time.sleep(0.05)
        
        if endpoint == "geolocate":
            return self._mock_geolocation(data)
        elif endpoint == "assess_risk":
            return self._mock_risk_assessment(data)
        elif endpoint == "get_risk_regions":
            return self._mock_risk_regions()
        else:
            return {"success": True, "message": "Mock response"}
    
    def _mock_geolocation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock IP geolocation."""
        ip_address = data.get("ip_address", "")
        
        # Simple mock logic based on IP patterns
        if ip_address.startswith("192.168.") or ip_address.startswith("10."):
            # Private IP - local network
            location_data = {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "country": "United States",
                "country_code": "US",
                "city": "New York",
                "region": "New York",
                "timezone": "America/New_York",
                "accuracy_radius": 1000,
                "is_vpn": False,
                "is_proxy": False,
                "is_tor": False
            }
        elif "vpn" in ip_address.lower() or ip_address.startswith("203."):
            # Mock VPN detection
            location_data = {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "country": "United Kingdom",
                "country_code": "GB",
                "city": "London",
                "region": "England",
                "timezone": "Europe/London",
                "accuracy_radius": 50,
                "is_vpn": True,
                "is_proxy": False,
                "is_tor": False
            }
        else:
            # Default US location
            location_data = {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "country": "United States",
                "country_code": "US",
                "city": "San Francisco",
                "region": "California",
                "timezone": "America/Los_Angeles",
                "accuracy_radius": 100,
                "is_vpn": False,
                "is_proxy": False,
                "is_tor": False
            }
        
        location_data["ip_address"] = ip_address
        return {"location": location_data}
    
    def _mock_risk_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock location risk assessment."""
        location_data = data.get("location", {})
        country = location_data.get("country", "")
        is_vpn = location_data.get("is_vpn", False)
        
        # Simple risk logic
        risk_factors = []
        risk_score = 0.2  # Base risk
        
        # VPN/Proxy risk
        if is_vpn:
            risk_factors.append("VPN/Proxy detected")
            risk_score += 0.4
        
        # Country-based risk
        high_risk_countries = ["Unknown", "Anonymous"]
        if country in high_risk_countries:
            risk_factors.append("High-risk country")
            risk_score += 0.3
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "very_high"
        elif risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        elif risk_score >= 0.2:
            risk_level = "low"
        else:
            risk_level = "very_low"
        
        # Verification status
        if risk_score >= 0.7:
            verification_status = "suspicious"
        elif risk_score >= 0.5:
            verification_status = "failed"
        else:
            verification_status = "verified"
        
        return {
            "risk_assessment": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "verification_status": verification_status,
                "confidence_score": 0.9 - (risk_score * 0.2),
                "recommendations": self._generate_risk_recommendations(risk_level, risk_factors)
            }
        }
    
    def _mock_risk_regions(self) -> Dict[str, Any]:
        """Mock high-risk regions data."""
        return {
            "risk_regions": [
                {
                    "country": "Anonymous Proxy",
                    "country_code": "A1",
                    "risk_level": "very_high",
                    "risk_factors": ["Anonymous proxy", "Identity concealment"]
                },
                {
                    "country": "Satellite Provider",
                    "country_code": "A2",
                    "risk_level": "high",
                    "risk_factors": ["Satellite connection", "Difficult to verify"]
                },
                {
                    "country": "Tor Network",
                    "country_code": "T1",
                    "risk_level": "very_high",
                    "risk_factors": ["Tor network", "Anonymization service"]
                }
            ]
        }
    
    def _generate_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> List[str]:
        """Generate recommendations based on risk assessment."""
        recommendations = []
        
        if risk_level in ["high", "very_high"]:
            recommendations.extend([
                "Require additional verification",
                "Consider manual review",
                "Implement enhanced monitoring"
            ])
        
        if "VPN/Proxy detected" in risk_factors:
            recommendations.append("Verify user identity through alternative means")
        
        if "High-risk country" in risk_factors:
            recommendations.append("Apply country-specific risk controls")
        
        if not recommendations:
            recommendations.append("Standard processing acceptable")
        
        return recommendations
    
    def _parse_location_response(self, data: Dict[str, Any]) -> GeographicLocation:
        """Parse API response into GeographicLocation object."""
        location_data = data.get("location", {})
        
        return GeographicLocation(
            latitude=float(location_data.get("latitude", 0.0)),
            longitude=float(location_data.get("longitude", 0.0)),
            country=location_data.get("country", "Unknown"),
            country_code=location_data.get("country_code", "XX"),
            city=location_data.get("city", "Unknown"),
            region=location_data.get("region"),
            postal_code=location_data.get("postal_code"),
            timezone=location_data.get("timezone"),
            ip_address=location_data.get("ip_address"),
            accuracy_radius=location_data.get("accuracy_radius"),
            is_vpn=location_data.get("is_vpn", False),
            is_proxy=location_data.get("is_proxy", False),
            is_tor=location_data.get("is_tor", False)
        )
    
    def _parse_risk_assessment(self, data: Dict[str, Any], location: GeographicLocation) -> LocationRiskAssessment:
        """Parse API response into LocationRiskAssessment object."""
        risk_data = data.get("risk_assessment", {})
        
        return LocationRiskAssessment(
            location=location,
            risk_level=LocationRiskLevel(risk_data.get("risk_level", "medium")),
            risk_score=float(risk_data.get("risk_score", 0.5)),
            risk_factors=risk_data.get("risk_factors", []),
            verification_status=LocationVerificationStatus(risk_data.get("verification_status", "unknown")),
            confidence_score=float(risk_data.get("confidence_score", 0.5)),
            assessment_timestamp=datetime.now(),
            risk_details=risk_data.get("risk_details", {}),
            recommendations=risk_data.get("recommendations", [])
        )
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two geographic points using Haversine formula.
        
        Returns distance in kilometers.
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    def _analyze_travel_velocity(
        self, 
        distance_km: float, 
        time_hours: float, 
        velocity_kmh: float
    ) -> Tuple[TravelPattern, List[str]]:
        """Analyze travel velocity and determine pattern."""
        risk_indicators = []
        
        # Impossible travel (faster than commercial aircraft)
        if velocity_kmh > 1000:
            return TravelPattern.IMPOSSIBLE_TRAVEL, [
                f"Impossible travel speed: {velocity_kmh:.1f} km/h",
                "Potential location spoofing",
                "Geographic fraud indicator"
            ]
        
        # Very high velocity (faster than typical ground transport)
        if velocity_kmh > 300:
            risk_indicators.extend([
                f"High travel velocity: {velocity_kmh:.1f} km/h",
                "Potential air travel or fraud"
            ])
            
            if distance_km > 1000:
                return TravelPattern.FREQUENT_TRAVELER, risk_indicators
            else:
                return TravelPattern.SUSPICIOUS_VELOCITY, risk_indicators
        
        # Rapid location changes
        if time_hours < 1 and distance_km > 50:
            risk_indicators.append("Rapid location change detected")
            return TravelPattern.LOCATION_HOPPING, risk_indicators
        
        # Normal travel patterns
        return TravelPattern.NORMAL, risk_indicators


def create_geolocation_tool(
    tool_id: str,
    provider: str = "generic",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> GeolocationTool:
    """
    Create geolocation tool with common configurations.
    
    Args:
        tool_id: Unique identifier for the tool
        provider: Geolocation provider (maxmind, ipinfo, ipgeolocation, generic)
        api_key: API key for the service
        base_url: Base URL for the API
        
    Returns:
        GeolocationTool instance
    """
    # Provider-specific configurations
    provider_configs = {
        "maxmind": {
            "base_url": base_url or "https://geoip.maxmind.com/geoip/v2.1",
            "rate_limit_per_minute": 1000,
            "timeout_seconds": 10
        },
        "ipinfo": {
            "base_url": base_url or "https://ipinfo.io",
            "rate_limit_per_minute": 50000,
            "timeout_seconds": 5
        },
        "ipgeolocation": {
            "base_url": base_url or "https://api.ipgeolocation.io",
            "rate_limit_per_minute": 1000,
            "timeout_seconds": 10
        },
        "generic": {
            "base_url": base_url or "https://api.mock-geolocation.com",
            "rate_limit_per_minute": 100,
            "timeout_seconds": 15
        }
    }
    
    config_data = provider_configs.get(provider, provider_configs["generic"])
    
    config = ToolConfiguration(
        tool_id=tool_id,
        tool_name=f"Geolocation Service ({provider})",
        tool_type=ToolType.GEOLOCATION,
        base_url=config_data["base_url"],
        api_key=api_key,
        timeout_seconds=config_data["timeout_seconds"],
        rate_limit_per_minute=config_data["rate_limit_per_minute"],
        enable_caching=True,
        cache_ttl_seconds=3600,  # Cache for 1 hour
        custom_parameters={
            "provider": provider,
            "enable_risk_assessment": True,
            "max_travel_velocity": 1000,  # km/h
            "risk_threshold": 0.7
        }
    )
    
    return GeolocationTool(config)