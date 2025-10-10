"""
Identity Verification Integration

Provides integration with identity verification services for fraud detection,
including real-time identity checks, document verification, and KYC compliance.
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .tool_integrator import ExternalTool, ToolConfiguration, ToolResponse, ToolType

logger = logging.getLogger(__name__)


class IdentityVerificationResult(Enum):
    """Identity verification results."""
    VERIFIED = "verified"
    FAILED = "failed"
    PENDING = "pending"
    INSUFFICIENT_DATA = "insufficient_data"
    DOCUMENT_REQUIRED = "document_required"


class DocumentType(Enum):
    """Types of identity documents."""
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    SOCIAL_SECURITY_CARD = "social_security_card"


@dataclass
class IdentityData:
    """Identity data for verification."""
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    ssn: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    document_number: Optional[str] = None
    document_type: Optional[DocumentType] = None


@dataclass
class VerificationResult:
    """Identity verification result."""
    verification_id: str
    result: IdentityVerificationResult
    confidence_score: float
    risk_score: float
    verification_details: Dict[str, Any]
    matched_fields: List[str]
    failed_fields: List[str]
    warnings: List[str]
    recommendations: List[str]
    timestamp: datetime
    provider: str


class IdentityVerificationTool(ExternalTool):
    """
    Identity verification tool integration.
    
    Supports multiple identity verification providers with unified interface.
    """
    
    def __init__(self, config: ToolConfiguration):
        """Initialize identity verification tool."""
        super().__init__(config)
        self.provider = config.custom_parameters.get("provider", "generic")
        self.verification_threshold = config.custom_parameters.get("verification_threshold", 0.8)
        self.enable_document_verification = config.custom_parameters.get("enable_document_verification", True)
        
        logger.info(f"Initialized identity verification tool with provider: {self.provider}")
    
    def call_api(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make API call to identity verification service."""
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
    
    def verify_identity(self, identity_data: IdentityData) -> VerificationResult:
        """
        Verify identity using provided data.
        
        Args:
            identity_data: Identity information to verify
            
        Returns:
            VerificationResult with verification details
        """
        request_data = {
            "first_name": identity_data.first_name,
            "last_name": identity_data.last_name,
            "date_of_birth": identity_data.date_of_birth,
            "ssn": identity_data.ssn,
            "address": identity_data.address,
            "city": identity_data.city,
            "state": identity_data.state,
            "zip_code": identity_data.zip_code,
            "country": identity_data.country,
            "phone": identity_data.phone,
            "email": identity_data.email
        }
        
        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}
        
        response = self.call_api("verify", request_data)
        
        if response.success:
            return self._parse_verification_response(response)
        else:
            # Return failed verification result
            return VerificationResult(
                verification_id=f"failed_{int(time.time())}",
                result=IdentityVerificationResult.FAILED,
                confidence_score=0.0,
                risk_score=1.0,
                verification_details={"error": response.error_message},
                matched_fields=[],
                failed_fields=list(request_data.keys()),
                warnings=[f"Verification service error: {response.error_message}"],
                recommendations=["Retry verification", "Use alternative verification method"],
                timestamp=datetime.now(),
                provider=self.provider
            )
    
    def verify_document(self, document_data: Dict[str, Any]) -> VerificationResult:
        """
        Verify identity document.
        
        Args:
            document_data: Document information and image data
            
        Returns:
            VerificationResult with document verification details
        """
        if not self.enable_document_verification:
            return VerificationResult(
                verification_id=f"doc_disabled_{int(time.time())}",
                result=IdentityVerificationResult.FAILED,
                confidence_score=0.0,
                risk_score=1.0,
                verification_details={"error": "Document verification disabled"},
                matched_fields=[],
                failed_fields=["document"],
                warnings=["Document verification is disabled"],
                recommendations=["Enable document verification", "Use identity data verification"],
                timestamp=datetime.now(),
                provider=self.provider
            )
        
        response = self.call_api("verify_document", document_data)
        
        if response.success:
            return self._parse_verification_response(response)
        else:
            return VerificationResult(
                verification_id=f"doc_failed_{int(time.time())}",
                result=IdentityVerificationResult.FAILED,
                confidence_score=0.0,
                risk_score=1.0,
                verification_details={"error": response.error_message},
                matched_fields=[],
                failed_fields=["document"],
                warnings=[f"Document verification error: {response.error_message}"],
                recommendations=["Check document quality", "Try different document type"],
                timestamp=datetime.now(),
                provider=self.provider
            )
    
    def check_watchlist(self, identity_data: IdentityData) -> Dict[str, Any]:
        """
        Check identity against watchlists and sanctions lists.
        
        Args:
            identity_data: Identity information to check
            
        Returns:
            Dict containing watchlist check results
        """
        request_data = {
            "first_name": identity_data.first_name,
            "last_name": identity_data.last_name,
            "date_of_birth": identity_data.date_of_birth,
            "country": identity_data.country
        }
        
        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}
        
        response = self.call_api("check_watchlist", request_data)
        
        if response.success:
            return response.data
        else:
            return {
                "watchlist_match": False,
                "sanctions_match": False,
                "pep_match": False,
                "error": response.error_message,
                "timestamp": datetime.now().isoformat()
            }
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make HTTP request to identity verification service."""
        start_time = time.time()
        
        try:
            url = f"{self.config.base_url}/{endpoint}"
            
            # Prepare request based on provider
            if self.provider == "jumio":
                response_data = self._call_jumio_api(url, data)
            elif self.provider == "onfido":
                response_data = self._call_onfido_api(url, data)
            elif self.provider == "trulioo":
                response_data = self._call_trulioo_api(url, data)
            else:
                # Generic/mock implementation
                response_data = self._call_generic_api(url, data)
            
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
    
    def _call_jumio_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Jumio identity verification API."""
        # Jumio-specific API implementation
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FraudDetection/1.0"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_onfido_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Onfido identity verification API."""
        # Onfido-specific API implementation
        headers = {
            "Content-Type": "application/json"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_trulioo_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Trulioo identity verification API."""
        # Trulioo-specific API implementation
        headers = {
            "Content-Type": "application/json"
        }
        
        response = self.session.post(
            url,
            json=data,
            headers=headers,
            timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        
        return response.json()
    
    def _call_generic_api(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic/mock identity verification implementation."""
        # Mock implementation for testing and development
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Generate mock verification result
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        
        # Simple mock logic - names starting with 'A' are verified
        is_verified = first_name.upper().startswith('A') or last_name.upper().startswith('A')
        
        confidence_score = 0.95 if is_verified else 0.3
        risk_score = 0.1 if is_verified else 0.8
        
        matched_fields = []
        failed_fields = []
        
        for field in ["first_name", "last_name", "date_of_birth", "address"]:
            if field in data and data[field]:
                if is_verified:
                    matched_fields.append(field)
                else:
                    failed_fields.append(field)
        
        return {
            "verification_id": f"mock_{int(time.time())}",
            "result": "verified" if is_verified else "failed",
            "confidence_score": confidence_score,
            "risk_score": risk_score,
            "verification_details": {
                "provider": "mock",
                "method": "identity_data",
                "data_sources": ["credit_bureau", "public_records"]
            },
            "matched_fields": matched_fields,
            "failed_fields": failed_fields,
            "warnings": [] if is_verified else ["Low confidence match"],
            "recommendations": [] if is_verified else ["Provide additional documentation", "Manual review recommended"]
        }
    
    def _parse_verification_response(self, response: ToolResponse) -> VerificationResult:
        """Parse API response into VerificationResult."""
        data = response.data
        
        # Map result string to enum
        result_str = data.get("result", "failed").lower()
        if result_str == "verified":
            result = IdentityVerificationResult.VERIFIED
        elif result_str == "pending":
            result = IdentityVerificationResult.PENDING
        elif result_str == "insufficient_data":
            result = IdentityVerificationResult.INSUFFICIENT_DATA
        elif result_str == "document_required":
            result = IdentityVerificationResult.DOCUMENT_REQUIRED
        else:
            result = IdentityVerificationResult.FAILED
        
        return VerificationResult(
            verification_id=data.get("verification_id", f"unknown_{int(time.time())}"),
            result=result,
            confidence_score=float(data.get("confidence_score", 0.0)),
            risk_score=float(data.get("risk_score", 1.0)),
            verification_details=data.get("verification_details", {}),
            matched_fields=data.get("matched_fields", []),
            failed_fields=data.get("failed_fields", []),
            warnings=data.get("warnings", []),
            recommendations=data.get("recommendations", []),
            timestamp=datetime.now(),
            provider=self.provider
        )


def create_identity_verification_tool(
    tool_id: str,
    provider: str = "generic",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> IdentityVerificationTool:
    """
    Create identity verification tool with common configurations.
    
    Args:
        tool_id: Unique identifier for the tool
        provider: Identity verification provider (jumio, onfido, trulioo, generic)
        api_key: API key for the service
        base_url: Base URL for the API
        
    Returns:
        IdentityVerificationTool instance
    """
    # Provider-specific configurations
    provider_configs = {
        "jumio": {
            "base_url": base_url or "https://netverify.com/api/v4",
            "rate_limit_per_minute": 100,
            "timeout_seconds": 30
        },
        "onfido": {
            "base_url": base_url or "https://api.onfido.com/v3",
            "rate_limit_per_minute": 200,
            "timeout_seconds": 25
        },
        "trulioo": {
            "base_url": base_url or "https://api.globaldatacompany.com",
            "rate_limit_per_minute": 150,
            "timeout_seconds": 35
        },
        "generic": {
            "base_url": base_url or "https://api.mock-identity-verification.com",
            "rate_limit_per_minute": 60,
            "timeout_seconds": 30
        }
    }
    
    config_data = provider_configs.get(provider, provider_configs["generic"])
    
    config = ToolConfiguration(
        tool_id=tool_id,
        tool_name=f"Identity Verification ({provider})",
        tool_type=ToolType.IDENTITY_VERIFICATION,
        base_url=config_data["base_url"],
        api_key=api_key,
        timeout_seconds=config_data["timeout_seconds"],
        rate_limit_per_minute=config_data["rate_limit_per_minute"],
        enable_caching=True,
        cache_ttl_seconds=3600,  # Cache for 1 hour
        custom_parameters={
            "provider": provider,
            "verification_threshold": 0.8,
            "enable_document_verification": True
        }
    )
    
    return IdentityVerificationTool(config)