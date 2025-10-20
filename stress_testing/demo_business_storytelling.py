"""
Demo script for Business Storytelling Engine.

Demonstrates how the storytelling engine translates technical metrics
into compelling business narratives for different investor profiles.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import HeroMetrics, BusinessMetrics, SystemMetrics
from src.dashboards.business_storytelling_engine import (
    BusinessStorytellingEngine,
    InvestorProfile,
    NarrativeStyle
)


def create_sample_metrics():
    """Create sample metrics for demonstration."""
    hero_metrics = HeroMetrics(
        timestamp=datetime.utcnow(),
        total_transactions=1_250_000,
        fraud_blocked=12_500,
        money_saved=3_750_000.0,
        uptime_percentage=99.9,
        transactions_per_second=5000,
        avg_response_time_ms=150.0,
        ai_accuracy=0.95,
        ai_confidence=0.92,
        cost_per_transaction=0.025,
        roi_percentage=180.0,
        customer_satisfaction=0.92
    )
    
    business_metrics = BusinessMetrics(
        timestamp=datetime.utcnow(),
        transactions_processed=1_250_000,
        transactions_per_second=5000.0,
        fraud_detected=12_500,
        fraud_prevented_amount=3_750_000.0,
        fraud_detection_rate=0.01,
        fraud_detection_accuracy=0.95,
        cost_per_transaction=0.025,
        total_cost=31_250.0,
        roi_percentage=180.0,
        money_saved=3_750_000.0,
        payback_period_months=6.0,
        customer_impact_score=0.92,
        false_positive_impact=0.02,
        performance_vs_baseline=67.0,
        cost_vs_baseline=40.0
    )
    
    system_metrics = SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=5000.0,
        requests_total=1_250_000,
        requests_successful=1_247_500,
        requests_failed=2_500,
        avg_response_time_ms=150.0,
        p50_response_time_ms=120.0,
        p95_response_time_ms=280.0,
        p99_response_time_ms=450.0,
        max_response_time_ms=1200.0,
        error_rate=0.002,
        timeout_rate=0.001,
        cpu_utilization=0.65,
        memory_utilization=0.72,
        network_throughput_mbps=450.0
    )
    
    return hero_metrics, business_metrics, system_metrics


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


async def demo_investor_profiles():
    """Demonstrate narratives for different investor profiles."""
    print_section("BUSINESS STORYTELLING ENGINE DEMO")
    
    engine = BusinessStorytellingEngine()
    hero_metrics, business_metrics, system_metrics = create_sample_metrics()
    
    # Demo each investor profile
    profiles = [
        InvestorProfile.GENERAL,
        InvestorProfile.FINANCIAL,
        InvestorProfile.TECHNICAL,
        InvestorProfile.STRATEGIC,
        InvestorProfile.WARREN_BUFFETT,
        InvestorProfile.MARK_CUBAN,
        InvestorProfile.KEVIN_OLEARY,
        InvestorProfile.RICHARD_BRANSON
    ]
    
    for profile in profiles:
        print_section(f"INVESTOR PROFILE: {profile.value.upper().replace('_', ' ')}")
        
        # Executive summary
        print("📊 EXECUTIVE SUMMARY:")
        print("-" * 80)
        narrative = engine.generate_narrative(
            hero_metrics=hero_metrics,
            business_metrics=business_metrics,
            system_metrics=system_metrics,
            investor_profile=profile,
            style=NarrativeStyle.EXECUTIVE_SUMMARY
        )
        print(narrative)
        
        # Elevator pitch
        print("\n\n🎯 ELEVATOR PITCH (30 seconds):")
        print("-" * 80)
        pitch = engine.generate_narrative(
            hero_metrics=hero_metrics,
            business_metrics=business_metrics,
            investor_profile=profile,
            style=NarrativeStyle.ELEVATOR_PITCH
        )
        print(pitch)
        
        # Key highlights
        print("\n\n✨ KEY HIGHLIGHTS:")
        print("-" * 80)
        highlights = engine.generate_key_highlights(
            hero_metrics=hero_metrics,
            business_metrics=business_metrics,
            investor_profile=profile
        )
        for i, highlight in enumerate(highlights, 1):
            print(f"{i}. {highlight}")
        
        print("\n")
        await asyncio.sleep(0.1)  # Small delay for readability


async def demo_narrative_styles():
    """Demonstrate different narrative styles."""
    print_section("NARRATIVE STYLES DEMO")
    
    engine = BusinessStorytellingEngine()
    hero_metrics, business_metrics, system_metrics = create_sample_metrics()
    
    styles = [
        (NarrativeStyle.EXECUTIVE_SUMMARY, "Executive Summary"),
        (NarrativeStyle.ELEVATOR_PITCH, "Elevator Pitch"),
        (NarrativeStyle.PROBLEM_SOLUTION, "Problem-Solution"),
        (NarrativeStyle.HERO_JOURNEY, "Hero's Journey"),
        (NarrativeStyle.DETAILED_ANALYSIS, "Detailed Analysis")
    ]
    
    for style_enum, style_name in styles:
        print(f"\n📝 {style_name.upper()}:")
        print("-" * 80)
        narrative = engine.generate_narrative(
            hero_metrics=hero_metrics,
            business_metrics=business_metrics,
            system_metrics=system_metrics,
            investor_profile=InvestorProfile.GENERAL,
            style=style_enum
        )
        print(narrative)
        print("\n")


async def demo_technical_translation():
    """Demonstrate technical to business translation."""
    print_section("TECHNICAL TO BUSINESS TRANSLATION")
    
    engine = BusinessStorytellingEngine()
    
    technical_terms = [
        ('tps', 5000),
        ('p99_latency', 450),
        ('uptime', 99.9),
        ('accuracy', 0.95),
        ('cost_per_transaction', 0.025),
        ('roi', 180),
        ('auto_scaling', None),
        ('multi_agent', None),
        ('real_time_learning', None),
        ('circuit_breaker', None),
        ('graceful_degradation', None)
    ]
    
    print("Translating technical jargon to business language:\n")
    
    for term, value in technical_terms:
        translation = engine.translate_technical_to_business(term, value)
        print(f"• {term.upper()}")
        print(f"  → {translation}\n")


async def demo_complete_customization():
    """Demonstrate complete investor customization package."""
    print_section("COMPLETE INVESTOR CUSTOMIZATION PACKAGE")
    
    engine = BusinessStorytellingEngine()
    hero_metrics, business_metrics, system_metrics = create_sample_metrics()
    
    # Generate complete package for Warren Buffett profile
    print("Generating complete package for WARREN BUFFETT profile...\n")
    
    package = engine.generate_investor_customization(
        hero_metrics=hero_metrics,
        business_metrics=business_metrics,
        investor_profile=InvestorProfile.WARREN_BUFFETT
    )
    
    print(f"Investor Profile: {package['investor_profile']}")
    print(f"Generated: {package['timestamp']}\n")
    
    print("📊 NARRATIVE:")
    print("-" * 80)
    print(package['narrative'])
    
    print("\n\n🎯 ELEVATOR PITCH:")
    print("-" * 80)
    print(package['elevator_pitch'])
    
    print("\n\n✨ KEY HIGHLIGHTS:")
    print("-" * 80)
    for i, highlight in enumerate(package['key_highlights'], 1):
        print(f"{i}. {highlight}")
    
    print("\n\n🎯 FOCUS AREAS:")
    print("-" * 80)
    for i, area in enumerate(package['focus_areas'], 1):
        print(f"{i}. {area}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  BUSINESS STORYTELLING ENGINE - COMPREHENSIVE DEMO")
    print("  Translating Technical Metrics to Business Narratives")
    print("=" * 80)
    
    # Run demos
    await demo_investor_profiles()
    await demo_narrative_styles()
    await demo_technical_translation()
    await demo_complete_customization()
    
    print("\n" + "=" * 80)
    print("  DEMO COMPLETE")
    print("=" * 80 + "\n")
    
    print("The Business Storytelling Engine successfully:")
    print("✓ Generated narratives for 8 different investor profiles")
    print("✓ Demonstrated 5 different narrative styles")
    print("✓ Translated technical jargon to business language")
    print("✓ Created complete customization packages")
    print("\nThis engine enables investor-specific presentations that resonate")
    print("with each stakeholder's priorities and communication style.\n")


if __name__ == "__main__":
    asyncio.run(main())
