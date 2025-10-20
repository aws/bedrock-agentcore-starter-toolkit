"""
Demo script for Competitive Benchmark Calculator.

This script demonstrates the competitive benchmark system's capabilities
including performance comparison, improvement calculations, and unique
advantage identification.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics.competitive_benchmark_calculator import (
    CompetitiveBenchmarkCalculator,
    CompetitorType,
    BenchmarkCategory
)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_basic_comparison():
    """Demonstrate basic competitive comparison."""
    print_section("Basic Competitive Comparison")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    # Our system metrics (superior performance)
    our_metrics = {
        'fraud_detection_accuracy': 0.95,
        'false_positive_rate': 0.05,
        'cost_per_transaction': 0.02,
        'avg_response_time_ms': 200,
        'uptime_percentage': 99.9,
        'max_tps': 5000
    }
    
    print("Our System Metrics:")
    print(f"  Fraud Detection Accuracy: {our_metrics['fraud_detection_accuracy']*100:.1f}%")
    print(f"  False Positive Rate: {our_metrics['false_positive_rate']*100:.1f}%")
    print(f"  Cost per Transaction: ${our_metrics['cost_per_transaction']:.3f}")
    print(f"  Avg Response Time: {our_metrics['avg_response_time_ms']:.0f}ms")
    print(f"  System Uptime: {our_metrics['uptime_percentage']:.1f}%")
    print(f"  Max Throughput: {our_metrics['max_tps']:,} TPS")
    
    # Compare against industry average
    print("\n" + "-" * 80)
    print("Comparing against Industry Average...")
    print("-" * 80 + "\n")
    
    comparisons = calculator.compare_against_competitor(
        competitor_type=CompetitorType.INDUSTRY_AVERAGE,
        **our_metrics
    )
    
    for comp in comparisons:
        status = "✓ BETTER" if comp.is_better else "✗ WORSE"
        print(f"{status} | {comp.metric_name}")
        print(f"         Us: {comp.our_value:.3f}")
        print(f"         Them: {comp.competitor_value:.3f}")
        print(f"         Improvement: {comp.improvement_percentage:+.1f}%")
        print(f"         Category: {comp.category.value}")
        print()



def demo_all_competitors():
    """Demonstrate comparison against all competitor types."""
    print_section("Comparison Against All Competitor Types")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    our_metrics = {
        'fraud_detection_accuracy': 0.95,
        'false_positive_rate': 0.05,
        'cost_per_transaction': 0.02,
        'avg_response_time_ms': 200,
        'uptime_percentage': 99.9,
        'max_tps': 5000
    }
    
    all_comparisons = calculator.compare_against_all_competitors(**our_metrics)
    
    for competitor_type, comparisons in all_comparisons.items():
        competitor = calculator.competitors[competitor_type]
        print(f"\n{competitor.name}:")
        print("-" * 80)
        
        # Calculate win rate
        wins = sum(1 for c in comparisons if c.is_better)
        win_rate = (wins / len(comparisons)) * 100
        
        print(f"Win Rate: {wins}/{len(comparisons)} ({win_rate:.0f}%)")
        
        # Show top improvements
        sorted_comps = sorted(
            comparisons,
            key=lambda c: c.improvement_percentage,
            reverse=True
        )
        
        print("\nTop 3 Improvements:")
        for i, comp in enumerate(sorted_comps[:3], 1):
            print(f"  {i}. {comp.metric_name}: {comp.improvement_percentage:+.1f}%")


def demo_unique_advantages():
    """Demonstrate unique advantage generation."""
    print_section("Unique Competitive Advantages")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    our_metrics = {
        'fraud_detection_accuracy': 0.95,
        'false_positive_rate': 0.05,
        'cost_per_transaction': 0.02,
        'avg_response_time_ms': 200,
        'uptime_percentage': 99.9,
        'max_tps': 5000
    }
    
    comparisons = calculator.compare_against_competitor(
        competitor_type=CompetitorType.INDUSTRY_AVERAGE,
        **our_metrics
    )
    
    advantages = calculator.generate_unique_advantages(comparisons)
    
    print("Our Unique Competitive Advantages:\n")
    for i, advantage in enumerate(advantages, 1):
        print(f"{i}. {advantage}")


def demo_market_position():
    """Demonstrate market position calculation."""
    print_section("Market Position Analysis")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    # Test with different performance levels
    scenarios = [
        {
            'name': 'Superior Performance',
            'metrics': {
                'fraud_detection_accuracy': 0.95,
                'false_positive_rate': 0.05,
                'cost_per_transaction': 0.02,
                'avg_response_time_ms': 200,
                'uptime_percentage': 99.9,
                'max_tps': 5000
            }
        },
        {
            'name': 'Average Performance',
            'metrics': {
                'fraud_detection_accuracy': 0.85,
                'false_positive_rate': 0.10,
                'cost_per_transaction': 0.05,
                'avg_response_time_ms': 500,
                'uptime_percentage': 99.5,
                'max_tps': 2000
            }
        },
        {
            'name': 'Below Average Performance',
            'metrics': {
                'fraud_detection_accuracy': 0.75,
                'false_positive_rate': 0.15,
                'cost_per_transaction': 0.08,
                'avg_response_time_ms': 800,
                'uptime_percentage': 99.0,
                'max_tps': 1000
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 80)
        
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **scenario['metrics']
        )
        
        position, score = calculator.calculate_market_position(comparisons)
        
        print(f"Market Position: {position.upper()}")
        print(f"Overall Score: {score:.2f}")
        print(f"Interpretation: ", end="")
        
        if position == "market_leader":
            print("Clear market leader with superior performance across all metrics")
        elif position == "strong_challenger":
            print("Strong competitive position with significant advantages")
        elif position == "competitive":
            print("Competitive with industry standards")
        else:
            print("Developing position, needs improvement")



def demo_category_summary():
    """Demonstrate category-based summary."""
    print_section("Performance by Category")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    our_metrics = {
        'fraud_detection_accuracy': 0.95,
        'false_positive_rate': 0.05,
        'cost_per_transaction': 0.02,
        'avg_response_time_ms': 200,
        'uptime_percentage': 99.9,
        'max_tps': 5000
    }
    
    comparisons = calculator.compare_against_competitor(
        competitor_type=CompetitorType.INDUSTRY_AVERAGE,
        **our_metrics
    )
    
    summary = calculator.get_category_summary(comparisons)
    
    print("Performance Summary by Category:\n")
    
    for category, stats in summary.items():
        print(f"{category.value.upper()}:")
        print(f"  Metrics Compared: {stats['count']}")
        print(f"  Wins: {stats['wins']}/{stats['count']} ({stats['win_rate']*100:.0f}%)")
        print(f"  Average Improvement: {stats['avg_improvement']:+.1f}%")
        print(f"  Best Improvement: {stats['max_improvement']:+.1f}%")
        print()


def demo_complete_benchmarks():
    """Demonstrate complete competitive benchmarks generation."""
    print_section("Complete Competitive Benchmarks")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    our_metrics = {
        'fraud_detection_accuracy': 0.95,
        'false_positive_rate': 0.05,
        'cost_per_transaction': 0.02,
        'avg_response_time_ms': 200,
        'uptime_percentage': 99.9,
        'max_tps': 5000
    }
    
    # Generate complete benchmarks
    benchmarks = calculator.generate_competitive_benchmarks(
        **our_metrics,
        competitor_type=CompetitorType.INDUSTRY_AVERAGE
    )
    
    print("Complete Competitive Benchmark Report")
    print("-" * 80)
    print(f"Timestamp: {benchmarks.timestamp}")
    print(f"Market Position: {benchmarks.market_position.upper()}")
    print()
    
    print("Our Performance:")
    for metric, value in benchmarks.our_performance.items():
        print(f"  {metric}: {value}")
    print()
    
    print("Competitor Average:")
    for metric, value in benchmarks.competitor_avg.items():
        print(f"  {metric}: {value}")
    print()
    
    print("Improvement Percentages:")
    for metric, improvement in benchmarks.improvement_percentage.items():
        print(f"  {metric}: {improvement:+.1f}%")
    print()
    
    print(f"Unique Advantages ({len(benchmarks.unique_advantages)}):")
    for i, advantage in enumerate(benchmarks.unique_advantages, 1):
        print(f"  {i}. {advantage}")


def demo_formatted_report():
    """Demonstrate formatted comparison report."""
    print_section("Formatted Comparison Report")
    
    calculator = CompetitiveBenchmarkCalculator()
    
    our_metrics = {
        'fraud_detection_accuracy': 0.95,
        'false_positive_rate': 0.05,
        'cost_per_transaction': 0.02,
        'avg_response_time_ms': 200,
        'uptime_percentage': 99.9,
        'max_tps': 5000
    }
    
    comparisons = calculator.compare_against_competitor(
        competitor_type=CompetitorType.MODERN_AI,
        **our_metrics
    )
    
    report = calculator.format_comparison_report(
        comparisons,
        competitor_name="Modern AI Solutions"
    )
    
    print(report)


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  COMPETITIVE BENCHMARK CALCULATOR DEMO")
    print("=" * 80)
    
    try:
        demo_basic_comparison()
        demo_all_competitors()
        demo_unique_advantages()
        demo_market_position()
        demo_category_summary()
        demo_complete_benchmarks()
        demo_formatted_report()
        
        print("\n" + "=" * 80)
        print("  Demo completed successfully!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
