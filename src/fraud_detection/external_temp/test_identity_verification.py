"""
Unit tests for Identity Verification Integration.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.identity_verification import (
    IdentityVerificationTool, IdentityData, VerificationResult,
    IdentityVerificationResult, DocumentType, create_identity_verification_tool
)
from src.tool_integrator import ToolConfiguration, ToolType


@pytest.fixture
def identity_verification_config():
    """Create test configuration for identity verification tool."""
    return ToolConfiguration(
        tool_id="test_identity_verification",
        tool_name="Test Identity Verification",
        tool_type=ToolType.IDENTITY_VERIFICATION,
        base_url="https://api.test-identity.com",
        api_key="test_api_key",
        timeout_seconds=30,
        rate_limit_per_minute=60,
        custom_parameters={
            "provider": "generic",
            "verification_threshold": 0.8,
            "enable_document_verification": True
        }
    )


@pytest.fixture
def identity_verification_tool(identity_verification_config):
    """Create identity verification tool for testing."""
    return IdentityVerificationTool(identity_verification_config)


@pytest.fixture
def sample_identity_data():
    """Create sample identity data for testing."""
    return IdentityData(
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
    )


class TestIdentityVerificationTool:
    """Test cases for IdentityVerificationTool."""
    
    def test_tool_initialization(self, identity_verification_tool):
        """Test that identity verification tool initializes correctly."""
        assert identity_verification_tool.config.tool_name == "Test Identity Verification"
        assert identity_verification_tool.config.tool_type == ToolType.IDENTITY_VERIFICATION
        assert identity_verification_tool.provider == "generic"
        assert identity_verification_tool.verification_threshold == 0.8
        assert identity_verification_tool.enable_document_verification is True
    
    def test_verify_identity_success(self, identity_verification_tool, sample_identity_data):
        """Test successful identity verification."""
        # Mock the API call to return success
        with patch.object(identity_verification_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "verification_id": "test_verification_123",
                    "result": "verified",
                    "confidence_score": 0.95,
                    "risk_score": 0.1,
                    "verification_details": {
                        "provider": "generic",
                        "method": "identity_data"
                    },
                    "matched_fields": ["first_name", "last_name", "date_of_birth"],
                    "failed_fields": [],
                    "warnings": [],
                    "recommendations": []
                },
                response_time_ms=150.0,
                tool_id="test_identity_verification",
                timestamp=datetime.now()
            )
            
            result = identity_verification_tool.verify_identity(sample_identity_data)
            
            assert isinstance(result, VerificationResult)
            assert result.result == IdentityVerificationResult.VERIFIED
            assert result.confidence_score == 0.95
            assert result.risk_score == 0.1
            assert "first_name" in result.matched_fields
            assert len(result.failed_fields) == 0
    
    def test_verify_identity_failure(self, identity_verification_tool, sample_identity_data):
        """Test failed identity verification."""
        # Mock the API call to return failure
        with patch.object(identity_verification_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "verification_id": "test_verification_456",
                    "result": "failed",
                    "confidence_score": 0.3,
                    "risk_score": 0.8,
                    "verification_details": {
                        "provider": "generic",
                        "method": "identity_data"
                    },
                    "matched_fields": ["first_name"],
                    "failed_fields": ["last_name", "date_of_birth", "ssn"],
                    "warnings": ["Low confidence match"],
                    "recommendations": ["Provide additional documentation"]
                },
                response_time_ms=200.0,
                tool_id="test_identity_verification",
                timestamp=datetime.now()
            )
            
            result = identity_verification_tool.verify_identity(sample_identity_data)
            
            assert result.result == IdentityVerificationResult.FAILED
            assert result.confidence_score == 0.3
            assert result.risk_score == 0.8
            assert len(result.failed_fields) > 0
            assert len(result.warnings) > 0
    
    def test_verify_identity_api_error(self, identity_verification_tool, sample_identity_data):
        """Test identity verification with API error."""
        # Mock the API call to return error
        with patch.object(identity_verification_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=False,
                data={},
                error_message="API service unavailable",
                response_time_ms=5000.0,
                tool_id="test_identity_verification",
                timestamp=datetime.now()
            )
            
            result = identity_verification_tool.verify_identity(sample_identity_data)
            
            assert result.result == IdentityVerificationResult.FAILED
            assert result.confidence_score == 0.0
            assert result.risk_score == 1.0
            assert "error" in result.verification_details
            assert len(result.warnings) > 0
    
    def test_verify_document_success(self, identity_verification_tool):
        """Test successful document verification."""
        document_data = {
            "document_type": "drivers_license",
            "document_image": "base64_encoded_image_data",
            "document_number": "DL123456789"
        }
        
        with patch.object(identity_verification_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "verification_id": "doc_verification_123",
                    "result": "verified",
                    "confidence_score": 0.92,
                    "risk_score": 0.15,
                    "verification_details": {
                        "document_type": "drivers_license",
                        "document_authentic": True,
                        "text_extracted": True
                    },
                    "matched_fields": ["document_number", "name", "date_of_birth"],
                    "failed_fields": [],
                    "warnings": [],
                    "recommendations": []
                },
                response_time_ms=300.0,
                tool_id="test_identity_verification",
                timestamp=datetime.now()
            )
            
            result = identity_verification_tool.verify_document(document_data)
            
            assert result.result == IdentityVerificationResult.VERIFIED
            assert result.confidence_score == 0.92
            assert "document_number" in result.matched_fields
    
    def test_verify_document_disabled(self, identity_verification_config):
        """Test document verification when disabled."""
        # Disable document verification
        identity_verification_config.custom_parameters["enable_document_verification"] = False
        tool = IdentityVerificationTool(identity_verification_config)
        
        document_data = {
            "document_type": "passport",
            "document_image": "base64_encoded_image_data"
        }
        
        result = tool.verify_document(document_data)
        
        assert result.result == IdentityVerificationResult.FAILED
        assert "disabled" in result.verification_details["error"]
        assert "Enable document verification" in result.recommendations
    
    def test_check_watchlist_success(self, identity_verification_tool, sample_identity_data):
        """Test successful watchlist check."""
        with patch.object(identity_verification_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "watchlist_match": False,
                    "sanctions_match": False,
                    "pep_match": False,
                    "matches": [],
                    "timestamp": datetime.now().isoformat()
                },
                response_time_ms=100.0,
                tool_id="test_identity_verification",
                timestamp=datetime.now()
            )
            
            result = identity_verification_tool.check_watchlist(sample_identity_data)
            
            assert result["watchlist_match"] is False
            assert result["sanctions_match"] is False
            assert result["pep_match"] is False
            assert "matches" in result
    
    def test_check_watchlist_match_found(self, identity_verification_tool, sample_identity_data):
        """Test watchlist check with match found."""
        with patch.object(identity_verification_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "watchlist_match": True,
                    "sanctions_match": True,
                    "pep_match": False,
                    "matches": [
                        {
                            "list_name": "OFAC SDN",
                            "match_score": 0.95,
                            "matched_name": "Alice Anderson",
                            "list_entry": "ANDERSON, Alice"
                        }
                    ],
                    "timestamp": datetime.now().isoformat()
                },
                response_time_ms=120.0,
                tool_id="test_identity_verification",
                timestamp=datetime.now()
            )
            
            result = identity_verification_tool.check_watchlist(sample_identity_data)
            
            assert result["watchlist_match"] is True
            assert result["sanctions_match"] is True
            assert len(result["matches"]) > 0
            assert result["matches"][0]["match_score"] == 0.95
    
    def test_generic_api_mock_logic(self, identity_verification_tool):
        """Test the mock logic in generic API implementation."""
        # Test with name starting with 'A' (should be verified)
        identity_data_verified = IdentityData(
            first_name="Alice",
            last_name="Smith"
        )
        
        result_verified = identity_verification_tool.verify_identity(identity_data_verified)
        assert result_verified.result == IdentityVerificationResult.VERIFIED
        assert result_verified.confidence_score > 0.8
        
        # Test with name not starting with 'A' (should fail)
        identity_data_failed = IdentityData(
            first_name="Bob",
            last_name="Johnson"
        )
        
        result_failed = identity_verification_tool.verify_identity(identity_data_failed)
        assert result_failed.result == IdentityVerificationResult.FAILED
        assert result_failed.confidence_score < 0.5
    
    def test_rate_limiting(self, identity_verification_tool, sample_identity_data):
        """Test rate limiting functionality."""
        # Set a very low rate limit for testing
        identity_verification_tool.config.rate_limit_per_minute = 1
        
        # First request should succeed
        result1 = identity_verification_tool.verify_identity(sample_identity_data)
        assert result1.result in [IdentityVerificationResult.VERIFIED, IdentityVerificationResult.FAILED]
        
        # Second request should be rate limited
        with patch.object(identity_verification_tool, '_check_rate_limit', return_value=False):
            response = identity_verification_tool.call_api("verify", {"test": "data"})
            assert not response.success
            assert "Rate limit exceeded" in response.error_message
    
    def test_caching_functionality(self, identity_verification_tool, sample_identity_data):
        """Test response caching functionality."""
        # Enable caching
        identity_verification_tool.config.enable_caching = True
        identity_verification_tool.config.cache_ttl_seconds = 300
        
        # First request
        result1 = identity_verification_tool.verify_identity(sample_identity_data)
        
        # Second identical request should use cache
        result2 = identity_verification_tool.verify_identity(sample_identity_data)
        
        # Results should be the same
        assert result1.verification_id == result2.verification_id
        assert result1.confidence_score == result2.confidence_score
    
    def test_different_providers(self):
        """Test creating tools with different providers."""
        providers = ["jumio", "onfido", "trulioo", "generic"]
        
        for provider in providers:
            tool = create_identity_verification_tool(
                tool_id=f"test_{provider}",
                provider=provider,
                api_key="test_key"
            )
            
            assert tool.provider == provider
            assert tool.config.tool_id == f"test_{provider}"
            assert provider in tool.config.tool_name.lower()


class TestIdentityData:
    """Test cases for IdentityData dataclass."""
    
    def test_identity_data_creation(self):
        """Test creating IdentityData with various fields."""
        identity_data = IdentityData(
            first_name="John",
            last_name="Doe",
            date_of_birth="1985-05-15",
            ssn="987-65-4321",
            document_type=DocumentType.PASSPORT
        )
        
        assert identity_data.first_name == "John"
        assert identity_data.last_name == "Doe"
        assert identity_data.date_of_birth == "1985-05-15"
        assert identity_data.document_type == DocumentType.PASSPORT
    
    def test_identity_data_minimal(self):
        """Test creating IdentityData with minimal required fields."""
        identity_data = IdentityData(
            first_name="Jane",
            last_name="Smith"
        )
        
        assert identity_data.first_name == "Jane"
        assert identity_data.last_name == "Smith"
        assert identity_data.date_of_birth is None
        assert identity_data.ssn is None


class TestCreateIdentityVerificationTool:
    """Test cases for the factory function."""
    
    def test_create_generic_tool(self):
        """Test creating generic identity verification tool."""
        tool = create_identity_verification_tool(
            tool_id="test_generic",
            provider="generic"
        )
        
        assert tool.config.tool_id == "test_generic"
        assert tool.provider == "generic"
        assert "mock-identity-verification" in tool.config.base_url
    
    def test_create_jumio_tool(self):
        """Test creating Jumio identity verification tool."""
        tool = create_identity_verification_tool(
            tool_id="test_jumio",
            provider="jumio",
            api_key="jumio_api_key"
        )
        
        assert tool.config.tool_id == "test_jumio"
        assert tool.provider == "jumio"
        assert tool.config.api_key == "jumio_api_key"
        assert "netverify.com" in tool.config.base_url
    
    def test_create_with_custom_base_url(self):
        """Test creating tool with custom base URL."""
        custom_url = "https://custom-identity-api.com"
        tool = create_identity_verification_tool(
            tool_id="test_custom",
            provider="generic",
            base_url=custom_url
        )
        
        assert tool.config.base_url == custom_url


if __name__ == "__main__":
    pytest.main([__file__])