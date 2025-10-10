"""
Unit tests for Fraud Database Integration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from fraud_database import (
    FraudDatabaseTool, FraudCase, SimilarCase, FraudPattern, PatternMatch,
    FraudType, FraudCaseStatus, SimilarityMetric, create_fraud_database_tool
)
from tool_integrator import ToolConfiguration, ToolType


@pytest.fixture
def fraud_database_config():
    """Create test configuration for fraud database tool."""
    return ToolConfiguration(
        tool_id="test_fraud_database",
        tool_name="Test Fraud Database",
        tool_type=ToolType.FRAUD_DATABASE,
        base_url="https://api.test-fraud-db.com",
        api_key="test_api_key",
        timeout_seconds=30,
        rate_limit_per_minute=100,
        custom_parameters={
            "database_type": "generic",
            "similarity_threshold": 0.7,
            "enable_pattern_updates": True,
            "max_similar_cases": 10
        }
    )


@pytest.fixture
def fraud_database_tool(fraud_database_config):
    """Create fraud database tool for testing."""
    return FraudDatabaseTool(fraud_database_config)


@pytest.fixture
def sample_transaction_data():
    """Create sample transaction data for testing."""
    return {
        "transaction_id": "tx_123456",
        "amount": 1500.00,
        "currency": "USD",
        "merchant": "Online Electronics Store",
        "category": "electronics",
        "timestamp": datetime.now().isoformat(),
        "user_id": "user_789",
        "card_type": "credit",
        "location": {
            "country": "US",
            "city": "New York",
            "ip_address": "192.168.1.1"
        }
    }


@pytest.fixture
def sample_fraud_case():
    """Create sample fraud case for testing."""
    return FraudCase(
        case_id="case_123456",
        fraud_type=FraudType.CARD_NOT_PRESENT,
        status=FraudCaseStatus.CONFIRMED,
        transaction_data={
            "amount": 2500.00,
            "merchant": "Suspicious Store",
            "timestamp": datetime.now().isoformat()
        },
        user_data={
            "user_id": "user_456",
            "account_age_days": 30
        },
        detection_method="pattern_matching",
        confidence_score=0.95,
        financial_impact=2500.00,
        created_date=datetime.now(),
        updated_date=datetime.now(),
        tags=["high_amount", "new_merchant"],
        investigation_notes="Suspicious high-value transaction"
    )


class TestFraudDatabaseTool:
    """Test cases for FraudDatabaseTool."""
    
    def test_tool_initialization(self, fraud_database_tool):
        """Test that fraud database tool initializes correctly."""
        assert fraud_database_tool.config.tool_name == "Test Fraud Database"
        assert fraud_database_tool.config.tool_type == ToolType.FRAUD_DATABASE
        assert fraud_database_tool.database_type == "generic"
        assert fraud_database_tool.similarity_threshold == 0.7
        assert fraud_database_tool.enable_pattern_updates is True
        assert fraud_database_tool.max_similar_cases == 10
    
    def test_search_similar_cases_success(self, fraud_database_tool, sample_transaction_data):
        """Test successful similar case search."""
        # Mock the API call to return similar cases
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "similar_cases": [
                        {
                            "case_id": "case_001",
                            "similarity_score": 0.85,
                            "similarity_metrics": {
                                "exact_match": 0.9,
                                "fuzzy_match": 0.8,
                                "pattern_match": 0.85
                            },
                            "fraud_type": "card_not_present",
                            "status": "confirmed",
                            "match_reasons": ["Similar amount", "Same merchant"],
                            "transaction_data": {"amount": 1520.00, "merchant": "Online Electronics Store"},
                            "confidence_score": 0.9,
                            "created_date": datetime.now().isoformat()
                        }
                    ]
                },
                response_time_ms=150.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            similar_cases = fraud_database_tool.search_similar_cases(sample_transaction_data)
            
            assert len(similar_cases) == 1
            assert isinstance(similar_cases[0], SimilarCase)
            assert similar_cases[0].case_id == "case_001"
            assert similar_cases[0].similarity_score == 0.85
            assert similar_cases[0].fraud_type == FraudType.CARD_NOT_PRESENT
            assert similar_cases[0].status == FraudCaseStatus.CONFIRMED
            assert len(similar_cases[0].match_reasons) == 2
    
    def test_search_similar_cases_with_filters(self, fraud_database_tool, sample_transaction_data):
        """Test similar case search with fraud type filters."""
        user_data = {"user_id": "user_789", "account_age_days": 365}
        fraud_types = [FraudType.CARD_NOT_PRESENT, FraudType.VELOCITY_FRAUD]
        
        with patch.object(fraud_database_tool, 'call_api') as mock_call:
            mock_call.return_value = Mock(success=True, data={"similar_cases": []})
            
            fraud_database_tool.search_similar_cases(
                sample_transaction_data, 
                user_data, 
                fraud_types
            )
            
            # Verify the API was called with correct parameters
            mock_call.assert_called_once()
            call_args = mock_call.call_args[0]
            assert call_args[0] == "search_similar"
            
            call_data = mock_call.call_args[1]["data"] if "data" in mock_call.call_args[1] else mock_call.call_args[0][1]
            assert call_data["user_data"] == user_data
            assert call_data["fraud_types"] == ["card_not_present", "velocity_fraud"]
    
    def test_check_fraud_patterns_success(self, fraud_database_tool, sample_transaction_data):
        """Test successful fraud pattern checking."""
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "pattern_matches": [
                        {
                            "pattern_id": "high_amount_pattern",
                            "pattern_name": "High Amount Transaction",
                            "match_score": 0.9,
                            "fraud_type": "card_not_present",
                            "matched_criteria": ["amount > $1000"],
                            "risk_indicators": ["High financial impact"],
                            "recommended_action": "manual_review",
                            "confidence_level": "high"
                        }
                    ]
                },
                response_time_ms=100.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            pattern_matches = fraud_database_tool.check_fraud_patterns(sample_transaction_data)
            
            assert len(pattern_matches) == 1
            assert isinstance(pattern_matches[0], PatternMatch)
            assert pattern_matches[0].pattern_id == "high_amount_pattern"
            assert pattern_matches[0].match_score == 0.9
            assert pattern_matches[0].fraud_type == FraudType.CARD_NOT_PRESENT
            assert pattern_matches[0].recommended_action == "manual_review"
    
    def test_report_fraud_case_success(self, fraud_database_tool, sample_fraud_case):
        """Test successful fraud case reporting."""
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "success": True,
                    "case_id": sample_fraud_case.case_id,
                    "message": "Fraud case reported successfully"
                },
                response_time_ms=200.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            result = fraud_database_tool.report_fraud_case(sample_fraud_case)
            
            assert result is True
            mock_request.assert_called_once_with("report_case", {
                "case_id": sample_fraud_case.case_id,
                "fraud_type": sample_fraud_case.fraud_type.value,
                "status": sample_fraud_case.status.value,
                "transaction_data": sample_fraud_case.transaction_data,
                "user_data": sample_fraud_case.user_data,
                "detection_method": sample_fraud_case.detection_method,
                "confidence_score": sample_fraud_case.confidence_score,
                "financial_impact": sample_fraud_case.financial_impact,
                "tags": sample_fraud_case.tags,
                "investigation_notes": sample_fraud_case.investigation_notes
            })
    
    def test_update_case_status_success(self, fraud_database_tool):
        """Test successful case status update."""
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "success": True,
                    "case_id": "case_123",
                    "status": "resolved"
                },
                response_time_ms=100.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            result = fraud_database_tool.update_case_status(
                "case_123", 
                FraudCaseStatus.RESOLVED, 
                "Investigation completed"
            )
            
            assert result is True
    
    def test_get_fraud_statistics_success(self, fraud_database_tool):
        """Test successful fraud statistics retrieval."""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "total_cases": 1250,
                    "confirmed_fraud": 890,
                    "false_positives": 180,
                    "fraud_types": {
                        "card_not_present": 450,
                        "account_takeover": 220
                    },
                    "detection_accuracy": 0.92
                },
                response_time_ms=150.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            stats = fraud_database_tool.get_fraud_statistics(start_date, end_date)
            
            assert stats["total_cases"] == 1250
            assert stats["confirmed_fraud"] == 890
            assert stats["detection_accuracy"] == 0.92
            assert "card_not_present" in stats["fraud_types"]
    
    def test_get_latest_patterns_success(self, fraud_database_tool):
        """Test successful latest patterns retrieval."""
        last_update = datetime.now() - timedelta(days=7)
        
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=True,
                data={
                    "patterns": [
                        {
                            "pattern_id": "velocity_pattern",
                            "pattern_name": "High Velocity Transactions",
                            "fraud_type": "velocity_fraud",
                            "pattern_rules": {"transaction_count": "> 5 in 10 minutes"},
                            "detection_criteria": ["Multiple transactions"],
                            "confidence_threshold": 0.8,
                            "false_positive_rate": 0.05,
                            "effectiveness_score": 0.92,
                            "case_count": 156,
                            "last_updated": datetime.now().isoformat(),
                            "active": True
                        }
                    ]
                },
                response_time_ms=120.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            patterns = fraud_database_tool.get_latest_patterns(last_update)
            
            assert len(patterns) == 1
            assert isinstance(patterns[0], FraudPattern)
            assert patterns[0].pattern_id == "velocity_pattern"
            assert patterns[0].fraud_type == FraudType.VELOCITY_FRAUD
            assert patterns[0].effectiveness_score == 0.92
    
    def test_mock_similar_search(self, fraud_database_tool):
        """Test mock similar search functionality."""
        transaction_data = {
            "amount": 1200.00,
            "merchant": "Test Merchant"
        }
        
        # Test the mock implementation directly
        result = fraud_database_tool._mock_similar_search({"transaction_data": transaction_data})
        
        assert "similar_cases" in result
        similar_cases = result["similar_cases"]
        assert len(similar_cases) >= 1
        
        # Check first similar case
        first_case = similar_cases[0]
        assert "case_id" in first_case
        assert "similarity_score" in first_case
        assert first_case["similarity_score"] >= 0.7
        assert "match_reasons" in first_case
    
    def test_mock_pattern_check_high_amount(self, fraud_database_tool):
        """Test mock pattern check for high amount transactions."""
        transaction_data = {"amount": 1500.00}
        
        result = fraud_database_tool._mock_pattern_check({"transaction_data": transaction_data})
        
        assert "pattern_matches" in result
        pattern_matches = result["pattern_matches"]
        
        # Should detect high amount pattern
        high_amount_pattern = next(
            (p for p in pattern_matches if p["pattern_id"] == "high_amount_pattern"), 
            None
        )
        assert high_amount_pattern is not None
        assert high_amount_pattern["match_score"] == 0.9
        assert high_amount_pattern["fraud_type"] == "card_not_present"
    
    def test_api_error_handling(self, fraud_database_tool, sample_transaction_data):
        """Test API error handling."""
        with patch.object(fraud_database_tool, '_make_request') as mock_request:
            mock_request.return_value = Mock(
                success=False,
                data={},
                error_message="Database service unavailable",
                response_time_ms=5000.0,
                tool_id="test_fraud_database",
                timestamp=datetime.now()
            )
            
            # Test similar case search with error
            similar_cases = fraud_database_tool.search_similar_cases(sample_transaction_data)
            assert similar_cases == []
            
            # Test pattern check with error
            pattern_matches = fraud_database_tool.check_fraud_patterns(sample_transaction_data)
            assert pattern_matches == []
            
            # Test case reporting with error
            fraud_case = FraudCase(
                case_id="test_case",
                fraud_type=FraudType.CARD_NOT_PRESENT,
                status=FraudCaseStatus.SUSPECTED,
                transaction_data=sample_transaction_data,
                user_data={},
                detection_method="test",
                confidence_score=0.8,
                financial_impact=100.0,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
            result = fraud_database_tool.report_fraud_case(fraud_case)
            assert result is False
    
    def test_different_database_types(self):
        """Test creating tools with different database types."""
        database_types = ["kount", "sift", "featurespace", "generic"]
        
        for db_type in database_types:
            tool = create_fraud_database_tool(
                tool_id=f"test_{db_type}",
                database_type=db_type,
                api_key="test_key"
            )
            
            assert tool.database_type == db_type
            assert tool.config.tool_id == f"test_{db_type}"
            assert db_type in tool.config.tool_name.lower()


class TestFraudCase:
    """Test cases for FraudCase dataclass."""
    
    def test_fraud_case_creation(self):
        """Test creating FraudCase with all fields."""
        fraud_case = FraudCase(
            case_id="case_001",
            fraud_type=FraudType.IDENTITY_THEFT,
            status=FraudCaseStatus.INVESTIGATING,
            transaction_data={"amount": 500.0},
            user_data={"user_id": "user_123"},
            detection_method="ml_model",
            confidence_score=0.85,
            financial_impact=500.0,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            tags=["identity", "high_risk"],
            investigation_notes="Suspicious identity verification"
        )
        
        assert fraud_case.case_id == "case_001"
        assert fraud_case.fraud_type == FraudType.IDENTITY_THEFT
        assert fraud_case.status == FraudCaseStatus.INVESTIGATING
        assert fraud_case.confidence_score == 0.85
        assert len(fraud_case.tags) == 2


class TestSimilarCase:
    """Test cases for SimilarCase dataclass."""
    
    def test_similar_case_creation(self):
        """Test creating SimilarCase with similarity metrics."""
        similarity_metrics = {
            SimilarityMetric.EXACT_MATCH: 0.9,
            SimilarityMetric.FUZZY_MATCH: 0.8,
            SimilarityMetric.PATTERN_MATCH: 0.85
        }
        
        similar_case = SimilarCase(
            case_id="similar_001",
            similarity_score=0.85,
            similarity_metrics=similarity_metrics,
            fraud_type=FraudType.VELOCITY_FRAUD,
            status=FraudCaseStatus.CONFIRMED,
            match_reasons=["Similar amount", "Same time pattern"],
            transaction_data={"amount": 1000.0},
            confidence_score=0.9,
            created_date=datetime.now()
        )
        
        assert similar_case.case_id == "similar_001"
        assert similar_case.similarity_score == 0.85
        assert len(similar_case.similarity_metrics) == 3
        assert SimilarityMetric.EXACT_MATCH in similar_case.similarity_metrics
        assert similar_case.similarity_metrics[SimilarityMetric.EXACT_MATCH] == 0.9


class TestCreateFraudDatabaseTool:
    """Test cases for the factory function."""
    
    def test_create_generic_tool(self):
        """Test creating generic fraud database tool."""
        tool = create_fraud_database_tool(
            tool_id="test_generic",
            database_type="generic"
        )
        
        assert tool.config.tool_id == "test_generic"
        assert tool.database_type == "generic"
        assert "generic" in tool.config.base_url
    
    def test_create_kount_tool(self):
        """Test creating Kount fraud database tool."""
        tool = create_fraud_database_tool(
            tool_id="test_kount",
            database_type="kount",
            api_key="kount_api_key"
        )
        
        assert tool.config.tool_id == "test_kount"
        assert tool.database_type == "kount"
        assert tool.config.api_key == "kount_api_key"
        assert "kount.com" in tool.config.base_url
    
    def test_create_with_custom_base_url(self):
        """Test creating tool with custom base URL."""
        custom_url = "https://custom-fraud-db.com"
        tool = create_fraud_database_tool(
            tool_id="test_custom",
            database_type="generic",
            base_url=custom_url
        )
        
        assert tool.config.base_url == custom_url


if __name__ == "__main__":
    pytest.main([__file__])