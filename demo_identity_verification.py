"""
Demo script for Identity Verification Integration

Demonstrates the identity verification capabilities including:
- Real-time identity verification
- Document verification
- Watchlist and sanctions checking
- Multiple provider support
- Error handling and fallback mechanisms
"""

import sys
import os
from datetime import datetime

# Add project root to path for imports
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.tool_integrator import ToolIntegrator
from src.identity_verification import (
    IdentityVerificationTool, IdentityData, DocumentType,
    create_identity_verification_tool
)


def create_sample_identities():
    """Create sample identity data for testing."""
    identities = []
    
    # Verified identity (name starts with 'A' in mock logic)
    identities.append(IdentityData(
        first_name="Alice",
        last_name="Anderson",
        date_of_birth="1990-01-15",
        ssn="123-45-6789",
        address="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
        country="US",
        phone="+1-555-123-4567",
        email="alice.anderson@example.com"
    ))
    
    # Failed identity (name doesn't start with 'A' in mock logic)
    identities.append(IdentityData(
        first_name="Bob",
        last_name="Johnson",
        date_of_birth="1985-03-22",
        ssn="987-65-4321",
        address="456 Oak Ave",
        city="Los Angeles",
        state="CA",
        zip_code="90210",
        country="US",
        phone="+1-555-987-6543",
        email="bob.johnson@example.com"
    ))
    
    # Partial identity data
    identities.append(IdentityData(
        first_name="Charlie",
        last_name="Brown",
        email="charlie.brown@example.com"
    ))
    
    # International identity
    identities.append(IdentityData(
        first_name="Anna",
        last_name="Mueller",
        date_of_birth="1992-07-10",
        address="Hauptstraße 123",
        city="Berlin",
        country="DE",
        phone="+49-30-12345678",
        email="anna.mueller@example.de"
    ))
    
    return identities


def demo_basic_identity_verification():
    """Demonstrate basic identity verification functionality."""
    print("=" * 60)
    print("IDENTITY VERIFICATION DEMO - BASIC VERIFICATION")
    print("=" * 60)
    
    # Create identity verification tool
    tool = create_identity_verification_tool(
        tool_id="demo_identity_tool",
        provider="generic",
        api_key="demo_api_key"
    )
    
    identities = create_sample_identities()
    
    print(f"\nTesting identity verification for {len(identities)} identities...")
    
    for i, identity in enumerate(identities):
        print(f"\n--- Identity {i+1}: {identity.first_name} {identity.last_name} ---")
        print(f"Country: {identity.country or 'Not specified'}")
        print(f"Email: {identity.email or 'Not provided'}")
        
        # Perform identity verification
        result = tool.verify_identity(identity)
        
        print(f"Verification Result: {result.result.value}")
        print(f"Confidence Score: {result.confidence_score:.2f}")
        print(f"Risk Score: {result.risk_score:.2f}")
        print(f"Provider: {result.provider}")
        
        if result.matched_fields:
            print(f"Matched Fields: {', '.join(result.matched_fields)}")
        
        if result.failed_fields:
            print(f"Failed Fields: {', '.join(result.failed_fields)}")
        
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if result.recommendations:
            print("Recommendations:")
            for rec in result.recommendations[:2]:  # Show first 2
                print(f"  - {rec}")


def demo_document_verification():
    """Demonstrate document verification functionality."""
    print("\n" + "=" * 60)
    print("IDENTITY VERIFICATION DEMO - DOCUMENT VERIFICATION")
    print("=" * 60)
    
    tool = create_identity_verification_tool(
        tool_id="demo_doc_tool",
        provider="generic",
        api_key="demo_api_key"
    )
    
    # Sample document data
    documents = [
        {
            "document_type": "drivers_license",
            "document_image": "base64_encoded_dl_image_data_here",
            "document_number": "DL123456789",
            "issuing_state": "NY",
            "expiry_date": "2025-12-31"
        },
        {
            "document_type": "passport",
            "document_image": "base64_encoded_passport_image_data_here",
            "document_number": "P123456789",
            "issuing_country": "US",
            "expiry_date": "2028-06-15"
        },
        {
            "document_type": "national_id",
            "document_image": "base64_encoded_id_image_data_here",
            "document_number": "ID987654321",
            "issuing_country": "DE"
        }
    ]
    
    print(f"\nTesting document verification for {len(documents)} documents...")
    
    for i, doc_data in enumerate(documents):
        print(f"\n--- Document {i+1}: {doc_data['document_type']} ---")
        print(f"Document Number: {doc_data['document_number']}")
        print(f"Issuing Authority: {doc_data.get('issuing_state') or doc_data.get('issuing_country')}")
        
        # Perform document verification
        result = tool.verify_document(doc_data)
        
        print(f"Verification Result: {result.result.value}")
        print(f"Confidence Score: {result.confidence_score:.2f}")
        print(f"Risk Score: {result.risk_score:.2f}")
        
        if result.verification_details:
            details = result.verification_details
            if "document_authentic" in details:
                print(f"Document Authentic: {details['document_authentic']}")
            if "text_extracted" in details:
                print(f"Text Extracted: {details['text_extracted']}")
        
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")


def demo_watchlist_checking():
    """Demonstrate watchlist and sanctions checking."""
    print("\n" + "=" * 60)
    print("IDENTITY VERIFICATION DEMO - WATCHLIST CHECKING")
    print("=" * 60)
    
    tool = create_identity_verification_tool(
        tool_id="demo_watchlist_tool",
        provider="generic",
        api_key="demo_api_key"
    )
    
    # Sample identities for watchlist checking
    watchlist_identities = [
        IdentityData(
            first_name="John",
            last_name="Smith",
            date_of_birth="1980-01-01",
            country="US"
        ),
        IdentityData(
            first_name="Maria",
            last_name="Garcia",
            date_of_birth="1975-05-15",
            country="MX"
        ),
        IdentityData(
            first_name="Ahmed",
            last_name="Hassan",
            date_of_birth="1970-12-10",
            country="EG"
        )
    ]
    
    print(f"\nChecking {len(watchlist_identities)} identities against watchlists...")
    
    for i, identity in enumerate(watchlist_identities):
        print(f"\n--- Watchlist Check {i+1}: {identity.first_name} {identity.last_name} ---")
        print(f"Date of Birth: {identity.date_of_birth}")
        print(f"Country: {identity.country}")
        
        # Perform watchlist check
        result = tool.check_watchlist(identity)
        
        print(f"Watchlist Match: {result.get('watchlist_match', False)}")
        print(f"Sanctions Match: {result.get('sanctions_match', False)}")
        print(f"PEP Match: {result.get('pep_match', False)}")
        
        if result.get("matches"):
            print("Matches Found:")
            for match in result["matches"]:
                print(f"  - List: {match.get('list_name')}")
                print(f"    Score: {match.get('match_score', 0):.2f}")
                print(f"    Entry: {match.get('list_entry')}")
        else:
            print("No matches found")


def demo_multiple_providers():
    """Demonstrate multiple provider support."""
    print("\n" + "=" * 60)
    print("IDENTITY VERIFICATION DEMO - MULTIPLE PROVIDERS")
    print("=" * 60)
    
    # Create tools for different providers
    providers = ["generic", "jumio", "onfido", "trulioo"]
    tools = {}
    
    for provider in providers:
        tools[provider] = create_identity_verification_tool(
            tool_id=f"demo_{provider}_tool",
            provider=provider,
            api_key=f"{provider}_api_key"
        )
    
    # Test identity
    test_identity = IdentityData(
        first_name="Alice",
        last_name="Wilson",
        date_of_birth="1988-09-20",
        country="US"
    )
    
    print(f"\nTesting identity verification across {len(providers)} providers...")
    print(f"Identity: {test_identity.first_name} {test_identity.last_name}")
    
    for provider, tool in tools.items():
        print(f"\n--- Provider: {provider.upper()} ---")
        print(f"Base URL: {tool.config.base_url}")
        print(f"Rate Limit: {tool.config.rate_limit_per_minute}/min")
        
        # Only test with generic provider (others would need real API keys)
        if provider == "generic":
            result = tool.verify_identity(test_identity)
            print(f"Result: {result.result.value}")
            print(f"Confidence: {result.confidence_score:.2f}")
        else:
            print("Result: Skipped (requires real API key)")


def demo_tool_integrator():
    """Demonstrate tool integrator with fallback mechanisms."""
    print("\n" + "=" * 60)
    print("IDENTITY VERIFICATION DEMO - TOOL INTEGRATOR")
    print("=" * 60)
    
    # Create tool integrator
    integrator = ToolIntegrator()
    
    # Create multiple identity verification tools
    primary_tool = create_identity_verification_tool(
        tool_id="primary_identity_tool",
        provider="generic",
        api_key="primary_api_key"
    )
    
    fallback_tool = create_identity_verification_tool(
        tool_id="fallback_identity_tool",
        provider="generic",
        api_key="fallback_api_key"
    )
    
    # Register tools
    integrator.register_tool(primary_tool)
    integrator.register_tool(fallback_tool)
    
    # Set up fallback chain
    integrator.set_fallback_chain("primary_identity_tool", ["fallback_identity_tool"])
    
    print("Registered tools:")
    print(f"  - Primary: {primary_tool.config.tool_name}")
    print(f"  - Fallback: {fallback_tool.config.tool_name}")
    
    # Test tool integration
    test_data = {
        "first_name": "Alice",
        "last_name": "Cooper",
        "date_of_birth": "1990-01-01"
    }
    
    print(f"\nTesting tool integration with fallback...")
    
    # Call primary tool
    response = integrator.call_tool("primary_identity_tool", "verify", test_data)
    
    print(f"Response Success: {response.success}")
    print(f"Tool Used: {response.tool_id}")
    print(f"Response Time: {response.response_time_ms:.1f}ms")
    
    if "used_fallback" in response.metadata:
        print(f"Fallback Used: {response.metadata['used_fallback']}")
        print(f"Primary Tool: {response.metadata['primary_tool']}")
    
    # Get tool status
    print(f"\nTool Status:")
    status = integrator.get_all_tools_status()
    for tool_id, tool_status in status["tools"].items():
        if tool_status:
            metrics = tool_status["metrics"]
            print(f"  {tool_id}:")
            print(f"    Status: {tool_status['status']}")
            print(f"    Requests: {metrics['total_requests']}")
            print(f"    Success Rate: {metrics['success_rate']:.1f}%")


def demo_performance_monitoring():
    """Demonstrate performance monitoring and metrics."""
    print("\n" + "=" * 60)
    print("IDENTITY VERIFICATION DEMO - PERFORMANCE MONITORING")
    print("=" * 60)
    
    tool = create_identity_verification_tool(
        tool_id="perf_test_tool",
        provider="generic",
        api_key="perf_api_key"
    )
    
    # Perform multiple verifications to generate metrics
    test_identities = [
        IdentityData(first_name="Alice", last_name="Adams"),
        IdentityData(first_name="Bob", last_name="Brown"),
        IdentityData(first_name="Anna", last_name="Anderson"),
        IdentityData(first_name="Charlie", last_name="Clark"),
        IdentityData(first_name="Amy", last_name="Allen")
    ]
    
    print(f"Performing {len(test_identities)} verifications for metrics...")
    
    for identity in test_identities:
        result = tool.verify_identity(identity)
        print(f"  {identity.first_name} {identity.last_name}: {result.result.value}")
    
    # Display performance metrics
    status = tool.get_status()
    metrics = status["metrics"]
    
    print(f"\nPerformance Metrics:")
    print(f"  Total Requests: {metrics['total_requests']}")
    print(f"  Success Rate: {metrics['success_rate']:.1f}%")
    print(f"  Average Response Time: {metrics['average_response_time_ms']:.1f}ms")
    print(f"  Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%")
    print(f"  Rate Limit Hits: {metrics['rate_limit_hits']}")
    
    if metrics['last_request_time']:
        print(f"  Last Request: {metrics['last_request_time']}")


def main():
    """Run all identity verification demos."""
    print("🔍 IDENTITY VERIFICATION INTEGRATION DEMONSTRATION")
    print("This demo showcases identity verification capabilities for")
    print("fraud detection including real-time verification, document")
    print("validation, and watchlist checking.")
    
    try:
        demo_basic_identity_verification()
        demo_document_verification()
        demo_watchlist_checking()
        demo_multiple_providers()
        demo_tool_integrator()
        demo_performance_monitoring()
        
        print("\n" + "=" * 60)
        print("✅ IDENTITY VERIFICATION DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe identity verification integration demonstrated:")
        print("• Real-time identity verification with multiple data points")
        print("• Document verification and authenticity checking")
        print("• Watchlist and sanctions screening")
        print("• Multiple provider support (Jumio, Onfido, Trulioo)")
        print("• Fallback mechanisms and error handling")
        print("• Performance monitoring and caching")
        print("• Rate limiting and circuit breaker patterns")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()