"""
Demo script for Geolocation and Risk Assessment Services

Demonstrates the geolocation capabilities including:
- IP geolocation and verification
- Location-based risk assessment
- Travel pattern analysis
- Geographic fraud detection
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path for imports
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from external_tools.tool_integrator import ToolIntegrator
from external_tools.geolocation_services import (
    GeolocationTool, GeographicLocation, LocationRiskLevel, TravelPattern,
    create_geolocation_tool
)


def create_sample_ip_addresses():
    """Create sample IP addresses for testing."""
    return [
        "192.168.1.100",    # Private IP (local network)
        "8.8.8.8",          # Google DNS (US)
        "203.0.113.45",     # Mock VPN IP
        "10.0.0.1",         # Private IP (corporate network)
        "151.101.193.140",  # Reddit (US)
        "172.217.12.142"    # Google (US)
    ]


def create_sample_locations():
    """Create sample geographic locations for testing."""
    locations = []
    
    # New York location
    locations.append(GeographicLocation(
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
    ))
    
    # London VPN location
    locations.append(GeographicLocation(
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
    ))
    
    # Los Angeles location
    locations.append(GeographicLocation(
        latitude=34.0522,
        longitude=-118.2437,
        country="United States",
        country_code="US",
        city="Los Angeles",
        region="California",
        timezone="America/Los_Angeles",
        ip_address="151.101.193.140",
        accuracy_radius=200,
        is_vpn=False,
        is_proxy=False,
        is_tor=False
    ))
    
    # Tokyo location
    locations.append(GeographicLocation(
        latitude=35.6762,
        longitude=139.6503,
        country="Japan",
        country_code="JP",
        city="Tokyo",
        region="Tokyo",
        timezone="Asia/Tokyo",
        ip_address="172.217.12.142",
        accuracy_radius=150,
        is_vpn=False,
        is_proxy=False,
        is_tor=False
    ))
    
    return locations


def demo_ip_geolocation():
    """Demonstrate IP geolocation functionality."""
    print("=" * 60)
    print("GEOLOCATION DEMO - IP GEOLOCATION")
    print("=" * 60)
    
    # Create geolocation tool
    tool = create_geolocation_tool(
        tool_id="demo_geolocation",
        provider="generic",
        api_key="demo_api_key"
    )
    
    ip_addresses = create_sample_ip_addresses()
    
    print(f"\nGeolocating {len(ip_addresses)} IP addresses...")
    
    for i, ip_address in enumerate(ip_addresses):
        print(f"\n--- IP Address {i+1}: {ip_address} ---")
        
        # Geolocate IP address
        location = tool.geolocate_ip(ip_address)
        
        if location:
            print(f"Location: {location.city}, {location.country}")
            print(f"Coordinates: {location.latitude:.4f}, {location.longitude:.4f}")
            print(f"Timezone: {location.timezone or 'Unknown'}")
            print(f"Accuracy: ±{location.accuracy_radius or 0} km")
            
            # Check for anonymization services
            anonymization_flags = []
            if location.is_vpn:
                anonymization_flags.append("VPN")
            if location.is_proxy:
                anonymization_flags.append("Proxy")
            if location.is_tor:
                anonymization_flags.append("Tor")
            
            if anonymization_flags:
                print(f"⚠️  Anonymization: {', '.join(anonymization_flags)}")
            else:
                print("✅ Direct connection detected")
        else:
            print("❌ Failed to geolocate IP address")


def demo_location_risk_assessment():
    """Demonstrate location-based risk assessment."""
    print("\n" + "=" * 60)
    print("GEOLOCATION DEMO - RISK ASSESSMENT")
    print("=" * 60)
    
    tool = create_geolocation_tool(
        tool_id="demo_risk_assessment",
        provider="generic",
        api_key="demo_api_key"
    )
    
    locations = create_sample_locations()
    
    print(f"\nAssessing risk for {len(locations)} locations...")
    
    for i, location in enumerate(locations):
        print(f"\n--- Location {i+1}: {location.city}, {location.country} ---")
        print(f"IP Address: {location.ip_address}")
        print(f"Coordinates: {location.latitude:.4f}, {location.longitude:.4f}")
        
        # Assess location risk
        user_context = {
            "user_id": f"user_{i+1}",
            "account_age_days": 365 - (i * 90),
            "previous_countries": ["US"] if i == 0 else ["US", "GB"]
        }
        
        assessment = tool.assess_location_risk(location, user_context)
        
        print(f"Risk Level: {assessment.risk_level.value.upper()}")
        print(f"Risk Score: {assessment.risk_score:.2f}")
        print(f"Verification: {assessment.verification_status.value}")
        print(f"Confidence: {assessment.confidence_score:.2f}")
        
        if assessment.risk_factors:
            print("Risk Factors:")
            for factor in assessment.risk_factors:
                print(f"  • {factor}")
        
        if assessment.recommendations:
            print("Recommendations:")
            for rec in assessment.recommendations[:2]:  # Show first 2
                print(f"  • {rec}")
        
        # Risk level indicator
        if assessment.risk_level in [LocationRiskLevel.HIGH, LocationRiskLevel.VERY_HIGH]:
            print("🚨 HIGH RISK - Additional verification required")
        elif assessment.risk_level == LocationRiskLevel.MEDIUM:
            print("⚠️  MEDIUM RISK - Monitor closely")
        else:
            print("✅ LOW RISK - Standard processing")


def demo_travel_pattern_analysis():
    """Demonstrate travel pattern analysis."""
    print("\n" + "=" * 60)
    print("GEOLOCATION DEMO - TRAVEL PATTERN ANALYSIS")
    print("=" * 60)
    
    tool = create_geolocation_tool(
        tool_id="demo_travel_analysis",
        provider="generic",
        api_key="demo_api_key"
    )
    
    locations = create_sample_locations()
    
    # Create travel scenarios
    travel_scenarios = [
        {
            "name": "Normal Local Travel",
            "user_id": "user_001",
            "previous": locations[0],  # New York
            "current": locations[0],   # Same location (slight movement)
            "time_diff": timedelta(hours=2)
        },
        {
            "name": "Cross-Country Travel",
            "user_id": "user_002", 
            "previous": locations[0],  # New York
            "current": locations[2],   # Los Angeles
            "time_diff": timedelta(hours=6)  # Flight time
        },
        {
            "name": "Impossible Travel",
            "user_id": "user_003",
            "previous": locations[0],  # New York
            "current": locations[3],   # Tokyo
            "time_diff": timedelta(minutes=30)  # Too fast!
        },
        {
            "name": "International VPN",
            "user_id": "user_004",
            "previous": locations[0],  # New York
            "current": locations[1],   # London (VPN)
            "time_diff": timedelta(hours=1)
        }
    ]
    
    print(f"\nAnalyzing {len(travel_scenarios)} travel scenarios...")
    
    for scenario in travel_scenarios:
        print(f"\n--- Scenario: {scenario['name']} ---")
        print(f"User: {scenario['user_id']}")
        print(f"From: {scenario['previous'].city}, {scenario['previous'].country}")
        print(f"To: {scenario['current'].city}, {scenario['current'].country}")
        print(f"Time Difference: {scenario['time_diff']}")
        
        # Analyze travel pattern
        analysis = tool.analyze_travel_pattern(
            scenario['user_id'],
            scenario['current'],
            scenario['previous'],
            scenario['time_diff']
        )
        
        print(f"Distance: {analysis.distance_km:.1f} km")
        print(f"Velocity: {analysis.travel_velocity_kmh:.1f} km/h")
        print(f"Pattern: {analysis.travel_pattern.value.upper()}")
        print(f"Possible Travel: {'✅ Yes' if analysis.is_possible_travel else '❌ No'}")
        
        if analysis.risk_indicators:
            print("Risk Indicators:")
            for indicator in analysis.risk_indicators:
                print(f"  • {indicator}")
        
        # Pattern-specific alerts
        if analysis.travel_pattern == TravelPattern.IMPOSSIBLE_TRAVEL:
            print("🚨 FRAUD ALERT - Impossible travel detected!")
        elif analysis.travel_pattern == TravelPattern.SUSPICIOUS_VELOCITY:
            print("⚠️  SUSPICIOUS - Unusually fast travel")
        elif analysis.travel_pattern == TravelPattern.LOCATION_HOPPING:
            print("⚠️  SUSPICIOUS - Rapid location changes")


def demo_location_verification():
    """Demonstrate location consistency verification."""
    print("\n" + "=" * 60)
    print("GEOLOCATION DEMO - LOCATION VERIFICATION")
    print("=" * 60)
    
    tool = create_geolocation_tool(
        tool_id="demo_verification",
        provider="generic",
        api_key="demo_api_key"
    )
    
    # Create verification scenarios
    verification_scenarios = [
        {
            "name": "Consistent Location",
            "claimed": locations[0],  # New York
            "detected": GeographicLocation(  # Manhattan (nearby)
                latitude=40.7589, longitude=-73.9851,
                country="United States", country_code="US", city="New York"
            ),
            "tolerance": 50.0
        },
        {
            "name": "Inconsistent Location", 
            "claimed": locations[0],  # New York
            "detected": locations[2], # Los Angeles
            "tolerance": 50.0
        },
        {
            "name": "International Mismatch",
            "claimed": locations[0],  # New York
            "detected": locations[3], # Tokyo
            "tolerance": 100.0
        }
    ]
    
    locations = create_sample_locations()
    
    print(f"\nVerifying location consistency for {len(verification_scenarios)} scenarios...")
    
    for scenario in verification_scenarios:
        print(f"\n--- Scenario: {scenario['name']} ---")
        print(f"Claimed: {scenario['claimed'].city}, {scenario['claimed'].country}")
        print(f"Detected: {scenario['detected'].city}, {scenario['detected'].country}")
        print(f"Tolerance: {scenario['tolerance']} km")
        
        # Verify location consistency
        result = tool.verify_location_consistency(
            scenario['claimed'],
            scenario['detected'],
            scenario['tolerance']
        )
        
        print(f"Distance Apart: {result['distance_km']:.1f} km")
        print(f"Consistent: {'✅ Yes' if result['is_consistent'] else '❌ No'}")
        print(f"Verification: {result['verification_status'].upper()}")
        print(f"Risk Level: {result['risk_level'].upper()}")
        
        if not result['is_consistent'] and 'risk_factors' in result:
            print("Risk Factors:")
            for factor in result['risk_factors']:
                print(f"  • {factor}")


def demo_high_risk_regions():
    """Demonstrate high-risk region detection."""
    print("\n" + "=" * 60)
    print("GEOLOCATION DEMO - HIGH-RISK REGIONS")
    print("=" * 60)
    
    tool = create_geolocation_tool(
        tool_id="demo_risk_regions",
        provider="generic",
        api_key="demo_api_key"
    )
    
    print("\nRetrieving high-risk geographic regions...")
    
    # Get high-risk regions
    risk_regions = tool.get_high_risk_regions()
    
    if risk_regions:
        print(f"Found {len(risk_regions)} high-risk regions:")
        
        for region in risk_regions:
            print(f"\n• {region['country']} ({region['country_code']})")
            print(f"  Risk Level: {region['risk_level'].upper()}")
            
            if 'risk_factors' in region:
                print(f"  Risk Factors: {', '.join(region['risk_factors'])}")
    else:
        print("No high-risk regions configured")
    
    # Test location against risk regions
    print(f"\n--- Testing Sample Locations Against Risk Regions ---")
    
    test_locations = [
        ("Normal US Location", "United States", "US"),
        ("VPN Location", "United Kingdom", "GB"),
        ("Anonymous Proxy", "Anonymous Proxy", "A1"),
        ("Tor Network", "Tor Network", "T1")
    ]
    
    for name, country, country_code in test_locations:
        print(f"\n{name} ({country}):")
        
        # Check if location matches any risk region
        matching_regions = [
            region for region in risk_regions 
            if region['country_code'] == country_code
        ]
        
        if matching_regions:
            region = matching_regions[0]
            print(f"  🚨 HIGH RISK REGION DETECTED")
            print(f"  Risk Level: {region['risk_level']}")
            print(f"  Factors: {', '.join(region.get('risk_factors', []))}")
        else:
            print(f"  ✅ Standard risk region")


def demo_tool_integration():
    """Demonstrate geolocation integration with tool integrator."""
    print("\n" + "=" * 60)
    print("GEOLOCATION DEMO - TOOL INTEGRATION")
    print("=" * 60)
    
    # Create tool integrator
    integrator = ToolIntegrator()
    
    # Create multiple geolocation tools
    primary_geo = create_geolocation_tool(
        tool_id="primary_geolocation",
        provider="generic",
        api_key="primary_api_key"
    )
    
    backup_geo = create_geolocation_tool(
        tool_id="backup_geolocation", 
        provider="generic",
        api_key="backup_api_key"
    )
    
    # Register tools
    integrator.register_tool(primary_geo)
    integrator.register_tool(backup_geo)
    
    # Set up fallback chain
    integrator.set_fallback_chain("primary_geolocation", ["backup_geolocation"])
    
    print("Registered geolocation tools:")
    print(f"  • Primary: {primary_geo.config.tool_name}")
    print(f"  • Backup: {backup_geo.config.tool_name}")
    
    # Test integrated geolocation
    test_ip = "8.8.8.8"
    
    print(f"\nTesting integrated geolocation for IP: {test_ip}")
    
    # Call through integrator
    response = integrator.call_tool(
        "primary_geolocation",
        "geolocate", 
        {"ip_address": test_ip}
    )
    
    print(f"Response Success: {response.success}")
    print(f"Tool Used: {response.tool_id}")
    print(f"Response Time: {response.response_time_ms:.1f}ms")
    
    if response.success and "location" in response.data:
        location_data = response.data["location"]
        print(f"Location: {location_data['city']}, {location_data['country']}")
        print(f"Coordinates: {location_data['latitude']}, {location_data['longitude']}")
    
    # Show tool health
    print(f"\nTool Health Status:")
    health = integrator.health_check()
    print(f"Overall Status: {health['overall_status']}")
    
    for tool_id, tool_health in health['tools'].items():
        print(f"  {tool_id}: {tool_health['health']} (success rate: {tool_health['success_rate']:.1f}%)")


def main():
    """Run all geolocation service demos."""
    print("🌍 GEOLOCATION AND RISK ASSESSMENT DEMONSTRATION")
    print("This demo showcases geolocation capabilities for")
    print("fraud detection including IP geolocation, risk assessment,")
    print("and travel pattern analysis.")
    
    try:
        demo_ip_geolocation()
        demo_location_risk_assessment()
        demo_travel_pattern_analysis()
        demo_location_verification()
        demo_high_risk_regions()
        demo_tool_integration()
        
        print("\n" + "=" * 60)
        print("✅ GEOLOCATION SERVICES DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe geolocation services demonstrated:")
        print("• IP geolocation with VPN/proxy detection")
        print("• Location-based risk assessment")
        print("• Travel pattern analysis and impossible travel detection")
        print("• Location consistency verification")
        print("• High-risk region identification")
        print("• Multi-provider integration with fallback support")
        print("• Performance monitoring and health checking")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()