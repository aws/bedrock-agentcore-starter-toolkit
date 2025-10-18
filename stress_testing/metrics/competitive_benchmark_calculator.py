"""
Competitive Benchmark Calculator.

Provides comprehensive competitive analysis and benchmark comparisons
for the fraud detection system against industry standards and competitors.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models import CompetitiveBenchmarks, SystemMetrics, BusinessMetrics


logger = logging.getLogger(__name__)


class CompetitorType(Enum):
    """Types of competitors for benchmarking."""
    TRADITIONAL_RULES = "traditional_rules"
    LEGACY_ML = "legacy_ml"
    MODERN_AI = "modern_ai"
    INDUSTRY_AVERAGE = "industry_average"


class BenchmarkCategory(Enum):
    """Categories for benchmark comparison."""
    PERFORMANCE = "performance"
    ACCURACY = "accuracy"
    COST = "cost"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    INNOVATION = "innovation"


@dataclass
class CompetitorProfile:
    """Profile of a competitor for benchmarking."""
    name: str
    competitor_type: CompetitorType
    fraud_detection_accuracy: float
    false_positive_rate: float
    cost_per_transaction: float
    avg_response_time_ms: float
    uptime_percentage: float
    max_tps: int
    features: List[str]


@dataclass
class BenchmarkComparison:
    """Detailed comparison for a specific metric."""
    metric_name: str
    our_value: float
    competitor_value: float
    improvement_percentage: float
    is_better: bool
    category: BenchmarkCategory
    description: str


class CompetitiveBenchmarkCalculator:
    """
    Calculates competitive benchmarks and generates comparison insights.
    
    This class provides comprehensive competitive analysis including:
    - Performance comparison against multiple competitor types
    - Improvement percentage calculations
    - Unique advantage identification
    - Market positioning analysis
    - Category-specific benchmarking
    """
    
    # Predefined competitor profiles based on industry research
    COMPETITOR_PROFILES = {
        CompetitorType.TRADITIONAL_RULES: CompetitorProfile(
            name="Traditional Rules-Based Systems",
            competitor_type=CompetitorType.TRADITIONAL_RULES,
            fraud_detection_accuracy=0.75,
            false_positive_rate=0.15,
            cost_per_transaction=0.08,
            avg_response_time_ms=800,
            uptime_percentage=99.0,
            max_tps=500,
            features=["Rule-based detection", "Manual review", "Basic reporting"]
        ),
        CompetitorType.LEGACY_ML: CompetitorProfile(
            name="Legacy Machine Learning Systems",
            competitor_type=CompetitorType.LEGACY_ML,
            fraud_detection_accuracy=0.82,
            false_positive_rate=0.12,
            cost_per_transaction=0.06,
            avg_response_time_ms=600,
            uptime_percentage=99.5,
            max_tps=1000,
            features=["ML models", "Batch processing", "Historical analysis"]
        ),
        CompetitorType.MODERN_AI: CompetitorProfile(
            name="Modern AI Solutions",
            competitor_type=CompetitorType.MODERN_AI,
            fraud_detection_accuracy=0.88,
            false_positive_rate=0.08,
            cost_per_transaction=0.04,
            avg_response_time_ms=400,
            uptime_percentage=99.7,
            max_tps=3000,
            features=["Deep learning", "Real-time processing", "API integration"]
        ),
        CompetitorType.INDUSTRY_AVERAGE: CompetitorProfile(
            name="Industry Average",
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            fraud_detection_accuracy=0.85,
            false_positive_rate=0.10,
            cost_per_transaction=0.05,
            avg_response_time_ms=500,
            uptime_percentage=99.5,
            max_tps=2000,
            features=["Mixed approaches", "Standard features"]
        )
    }

    
    def __init__(
        self,
        custom_competitors: Optional[Dict[str, CompetitorProfile]] = None
    ):
        """
        Initialize competitive benchmark calculator.
        
        Args:
            custom_competitors: Optional dictionary of custom competitor profiles
        """
        self.competitors = self.COMPETITOR_PROFILES.copy()
        if custom_competitors:
            self.competitors.update(custom_competitors)
        
        logger.info("CompetitiveBenchmarkCalculator initialized with %d competitor profiles", len(self.competitors))
    
    def calculate_improvement_percentage(
        self,
        our_value: float,
        competitor_value: float,
        higher_is_better: bool = True
    ) -> float:
        """
        Calculate improvement percentage compared to competitor.
        
        Args:
            our_value: Our metric value
            competitor_value: Competitor's metric value
            higher_is_better: Whether higher values are better (True) or lower is better (False)
            
        Returns:
            Improvement percentage (positive means we're better)
        """
        if competitor_value == 0:
            return 0.0
        
        if higher_is_better:
            # For metrics like accuracy, uptime where higher is better
            improvement = ((our_value - competitor_value) / competitor_value) * 100
        else:
            # For metrics like cost, latency where lower is better
            improvement = ((competitor_value - our_value) / competitor_value) * 100
        
        return improvement

    
    def compare_against_competitor(
        self,
        competitor_type: CompetitorType,
        fraud_detection_accuracy: float,
        false_positive_rate: float,
        cost_per_transaction: float,
        avg_response_time_ms: float,
        uptime_percentage: float,
        max_tps: int
    ) -> List[BenchmarkComparison]:
        """
        Compare our metrics against a specific competitor.
        
        Args:
            competitor_type: Type of competitor to compare against
            fraud_detection_accuracy: Our fraud detection accuracy
            false_positive_rate: Our false positive rate
            cost_per_transaction: Our cost per transaction
            avg_response_time_ms: Our average response time
            uptime_percentage: Our uptime percentage
            max_tps: Our maximum TPS capacity
            
        Returns:
            List of BenchmarkComparison objects
        """
        if competitor_type not in self.competitors:
            logger.warning(f"Competitor type {competitor_type} not found")
            return []
        
        competitor = self.competitors[competitor_type]
        comparisons = []
        
        # Accuracy comparison
        accuracy_improvement = self.calculate_improvement_percentage(
            fraud_detection_accuracy,
            competitor.fraud_detection_accuracy,
            higher_is_better=True
        )
        comparisons.append(BenchmarkComparison(
            metric_name="Fraud Detection Accuracy",
            our_value=fraud_detection_accuracy,
            competitor_value=competitor.fraud_detection_accuracy,
            improvement_percentage=accuracy_improvement,
            is_better=fraud_detection_accuracy > competitor.fraud_detection_accuracy,
            category=BenchmarkCategory.ACCURACY,
            description=f"{accuracy_improvement:+.1f}% accuracy improvement"
        ))
        
        # False positive rate comparison (lower is better)
        fpr_improvement = self.calculate_improvement_percentage(
            false_positive_rate,
            competitor.false_positive_rate,
            higher_is_better=False
        )
        comparisons.append(BenchmarkComparison(
            metric_name="False Positive Rate",
            our_value=false_positive_rate,
            competitor_value=competitor.false_positive_rate,
            improvement_percentage=fpr_improvement,
            is_better=false_positive_rate < competitor.false_positive_rate,
            category=BenchmarkCategory.ACCURACY,
            description=f"{fpr_improvement:+.1f}% reduction in false positives"
        ))

        
        # Cost comparison (lower is better)
        cost_improvement = self.calculate_improvement_percentage(
            cost_per_transaction,
            competitor.cost_per_transaction,
            higher_is_better=False
        )
        comparisons.append(BenchmarkComparison(
            metric_name="Cost per Transaction",
            our_value=cost_per_transaction,
            competitor_value=competitor.cost_per_transaction,
            improvement_percentage=cost_improvement,
            is_better=cost_per_transaction < competitor.cost_per_transaction,
            category=BenchmarkCategory.COST,
            description=f"{cost_improvement:+.1f}% cost reduction"
        ))
        
        # Response time comparison (lower is better)
        latency_improvement = self.calculate_improvement_percentage(
            avg_response_time_ms,
            competitor.avg_response_time_ms,
            higher_is_better=False
        )
        comparisons.append(BenchmarkComparison(
            metric_name="Average Response Time",
            our_value=avg_response_time_ms,
            competitor_value=competitor.avg_response_time_ms,
            improvement_percentage=latency_improvement,
            is_better=avg_response_time_ms < competitor.avg_response_time_ms,
            category=BenchmarkCategory.PERFORMANCE,
            description=f"{latency_improvement:+.1f}% faster response time"
        ))
        
        # Uptime comparison (higher is better)
        uptime_improvement = self.calculate_improvement_percentage(
            uptime_percentage,
            competitor.uptime_percentage,
            higher_is_better=True
        )
        comparisons.append(BenchmarkComparison(
            metric_name="System Uptime",
            our_value=uptime_percentage,
            competitor_value=competitor.uptime_percentage,
            improvement_percentage=uptime_improvement,
            is_better=uptime_percentage > competitor.uptime_percentage,
            category=BenchmarkCategory.RELIABILITY,
            description=f"{uptime_improvement:+.1f}% uptime improvement"
        ))
        
        # Throughput comparison (higher is better)
        tps_improvement = self.calculate_improvement_percentage(
            max_tps,
            competitor.max_tps,
            higher_is_better=True
        )
        comparisons.append(BenchmarkComparison(
            metric_name="Maximum Throughput (TPS)",
            our_value=max_tps,
            competitor_value=competitor.max_tps,
            improvement_percentage=tps_improvement,
            is_better=max_tps > competitor.max_tps,
            category=BenchmarkCategory.SCALABILITY,
            description=f"{tps_improvement:+.1f}% higher throughput capacity"
        ))
        
        logger.debug(
            f"Compared against {competitor.name}: "
            f"accuracy {accuracy_improvement:+.1f}%, cost {cost_improvement:+.1f}%"
        )
        
        return comparisons

    
    def generate_unique_advantages(
        self,
        comparisons: List[BenchmarkComparison],
        our_features: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate list of unique competitive advantages.
        
        Args:
            comparisons: List of benchmark comparisons
            our_features: Optional list of our unique features
            
        Returns:
            List of unique advantage descriptions
        """
        advantages = []
        
        # Analyze comparisons for significant advantages
        for comparison in comparisons:
            if comparison.is_better and comparison.improvement_percentage > 10:
                if comparison.improvement_percentage > 50:
                    advantages.append(
                        f"Exceptional {comparison.metric_name.lower()}: "
                        f"{comparison.improvement_percentage:.0f}% better than competitors"
                    )
                elif comparison.improvement_percentage > 25:
                    advantages.append(
                        f"Superior {comparison.metric_name.lower()}: "
                        f"{comparison.improvement_percentage:.0f}% improvement"
                    )
        
        # Add feature-based advantages
        default_features = [
            "Multi-agent AI coordination for comprehensive fraud analysis",
            "Explainable AI with chain-of-thought reasoning",
            "Real-time adaptive learning without downtime",
            "AWS serverless architecture for automatic scaling",
            "Sub-second fraud detection with high accuracy",
            "Zero-downtime deployment and updates",
            "Comprehensive audit trail for compliance",
            "Multi-currency and global transaction support"
        ]
        
        features = our_features or default_features
        advantages.extend(features[:4])  # Add top 4 unique features
        
        logger.info(f"Generated {len(advantages)} unique advantages")
        
        return advantages

    
    def calculate_market_position(
        self,
        comparisons: List[BenchmarkComparison]
    ) -> Tuple[str, float]:
        """
        Calculate overall market position based on comparisons.
        
        Args:
            comparisons: List of benchmark comparisons
            
        Returns:
            Tuple of (market_position, overall_score)
        """
        if not comparisons:
            return "unknown", 0.0
        
        # Calculate weighted score across all comparisons
        category_weights = {
            BenchmarkCategory.ACCURACY: 0.30,
            BenchmarkCategory.PERFORMANCE: 0.20,
            BenchmarkCategory.COST: 0.20,
            BenchmarkCategory.RELIABILITY: 0.15,
            BenchmarkCategory.SCALABILITY: 0.10,
            BenchmarkCategory.INNOVATION: 0.05
        }
        
        category_scores = {}
        category_counts = {}
        
        for comparison in comparisons:
            category = comparison.category
            if category not in category_scores:
                category_scores[category] = 0.0
                category_counts[category] = 0
            
            # Convert improvement percentage to score (1.0 = same, >1.0 = better)
            score = 1.0 + (comparison.improvement_percentage / 100.0)
            category_scores[category] += score
            category_counts[category] += 1
        
        # Calculate weighted average
        overall_score = 0.0
        for category, weight in category_weights.items():
            if category in category_scores and category_counts[category] > 0:
                avg_score = category_scores[category] / category_counts[category]
                overall_score += avg_score * weight
            else:
                overall_score += 1.0 * weight  # Neutral score if no data
        
        # Determine market position
        if overall_score >= 1.4:
            market_position = "market_leader"
        elif overall_score >= 1.2:
            market_position = "strong_challenger"
        elif overall_score >= 1.0:
            market_position = "competitive"
        else:
            market_position = "developing"
        
        logger.info(f"Market position: {market_position} (score: {overall_score:.2f})")
        
        return market_position, overall_score

    
    def generate_competitive_benchmarks(
        self,
        fraud_detection_accuracy: float,
        false_positive_rate: float,
        cost_per_transaction: float,
        avg_response_time_ms: float,
        uptime_percentage: float,
        max_tps: int = 5000,
        competitor_type: CompetitorType = CompetitorType.INDUSTRY_AVERAGE,
        our_features: Optional[List[str]] = None
    ) -> CompetitiveBenchmarks:
        """
        Generate comprehensive competitive benchmarks.
        
        This is the main method that combines all competitive analysis
        into a single CompetitiveBenchmarks object.
        
        Args:
            fraud_detection_accuracy: Our fraud detection accuracy
            false_positive_rate: Our false positive rate
            cost_per_transaction: Our cost per transaction
            avg_response_time_ms: Our average response time
            uptime_percentage: Our uptime percentage
            max_tps: Our maximum TPS capacity
            competitor_type: Type of competitor to compare against
            our_features: Optional list of our unique features
            
        Returns:
            CompetitiveBenchmarks object with complete comparison data
        """
        # Get comparisons against specified competitor
        comparisons = self.compare_against_competitor(
            competitor_type=competitor_type,
            fraud_detection_accuracy=fraud_detection_accuracy,
            false_positive_rate=false_positive_rate,
            cost_per_transaction=cost_per_transaction,
            avg_response_time_ms=avg_response_time_ms,
            uptime_percentage=uptime_percentage,
            max_tps=max_tps
        )
        
        # Build performance dictionaries
        our_performance = {
            'fraud_detection_accuracy': fraud_detection_accuracy,
            'false_positive_rate': false_positive_rate,
            'cost_per_transaction': cost_per_transaction,
            'avg_response_time_ms': avg_response_time_ms,
            'uptime_percentage': uptime_percentage,
            'max_tps': max_tps
        }
        
        competitor = self.competitors[competitor_type]
        competitor_avg = {
            'fraud_detection_accuracy': competitor.fraud_detection_accuracy,
            'false_positive_rate': competitor.false_positive_rate,
            'cost_per_transaction': competitor.cost_per_transaction,
            'avg_response_time_ms': competitor.avg_response_time_ms,
            'uptime_percentage': competitor.uptime_percentage,
            'max_tps': competitor.max_tps
        }
        
        # Build improvement percentages dictionary
        improvement_percentage = {
            comp.metric_name.lower().replace(' ', '_'): comp.improvement_percentage
            for comp in comparisons
        }
        
        # Generate unique advantages
        unique_advantages = self.generate_unique_advantages(comparisons, our_features)
        
        # Calculate market position
        market_position, _ = self.calculate_market_position(comparisons)
        
        benchmarks = CompetitiveBenchmarks(
            timestamp=datetime.utcnow(),
            our_performance=our_performance,
            competitor_avg=competitor_avg,
            improvement_percentage=improvement_percentage,
            unique_advantages=unique_advantages,
            market_position=market_position
        )
        
        logger.info(
            f"Generated competitive benchmarks: position={market_position}, "
            f"{len(unique_advantages)} advantages identified"
        )
        
        return benchmarks

    
    def compare_against_all_competitors(
        self,
        fraud_detection_accuracy: float,
        false_positive_rate: float,
        cost_per_transaction: float,
        avg_response_time_ms: float,
        uptime_percentage: float,
        max_tps: int = 5000
    ) -> Dict[CompetitorType, List[BenchmarkComparison]]:
        """
        Compare against all competitor types.
        
        Args:
            fraud_detection_accuracy: Our fraud detection accuracy
            false_positive_rate: Our false positive rate
            cost_per_transaction: Our cost per transaction
            avg_response_time_ms: Our average response time
            uptime_percentage: Our uptime percentage
            max_tps: Our maximum TPS capacity
            
        Returns:
            Dictionary mapping competitor types to their comparisons
        """
        all_comparisons = {}
        
        for competitor_type in self.competitors.keys():
            comparisons = self.compare_against_competitor(
                competitor_type=competitor_type,
                fraud_detection_accuracy=fraud_detection_accuracy,
                false_positive_rate=false_positive_rate,
                cost_per_transaction=cost_per_transaction,
                avg_response_time_ms=avg_response_time_ms,
                uptime_percentage=uptime_percentage,
                max_tps=max_tps
            )
            all_comparisons[competitor_type] = comparisons
        
        logger.info(f"Compared against {len(all_comparisons)} competitor types")
        
        return all_comparisons
    
    def get_category_summary(
        self,
        comparisons: List[BenchmarkComparison]
    ) -> Dict[BenchmarkCategory, Dict[str, Any]]:
        """
        Get summary statistics by category.
        
        Args:
            comparisons: List of benchmark comparisons
            
        Returns:
            Dictionary with category summaries
        """
        category_summary = {}
        
        for category in BenchmarkCategory:
            category_comps = [c for c in comparisons if c.category == category]
            
            if not category_comps:
                continue
            
            improvements = [c.improvement_percentage for c in category_comps]
            wins = sum(1 for c in category_comps if c.is_better)
            
            category_summary[category] = {
                'count': len(category_comps),
                'wins': wins,
                'win_rate': wins / len(category_comps) if category_comps else 0,
                'avg_improvement': sum(improvements) / len(improvements) if improvements else 0,
                'max_improvement': max(improvements) if improvements else 0,
                'min_improvement': min(improvements) if improvements else 0
            }
        
        return category_summary
    
    def format_comparison_report(
        self,
        comparisons: List[BenchmarkComparison],
        competitor_name: str = "Competitor"
    ) -> str:
        """
        Format comparisons into a readable report.
        
        Args:
            comparisons: List of benchmark comparisons
            competitor_name: Name of the competitor
            
        Returns:
            Formatted report string
        """
        lines = [
            f"Competitive Benchmark Report vs {competitor_name}",
            "=" * 60,
            ""
        ]
        
        # Group by category
        by_category = {}
        for comp in comparisons:
            if comp.category not in by_category:
                by_category[comp.category] = []
            by_category[comp.category].append(comp)
        
        # Format each category
        for category, comps in by_category.items():
            lines.append(f"{category.value.upper()}:")
            lines.append("-" * 60)
            
            for comp in comps:
                status = "✓" if comp.is_better else "✗"
                lines.append(
                    f"{status} {comp.metric_name}: "
                    f"{comp.our_value:.3f} vs {comp.competitor_value:.3f} "
                    f"({comp.improvement_percentage:+.1f}%)"
                )
            
            lines.append("")
        
        return "\n".join(lines)
