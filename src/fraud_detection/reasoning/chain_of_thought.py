#!/usr/bin/env python3
"""
Chain-of-Thought Reasoning Module
Advanced LLM reasoning with multi-step analysis for fraud detection
"""

import json
import logging
import boto3
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReasoningStepType(Enum):
    """Types of reasoning steps"""
    OBSERVATION = "observation"
    ANALYSIS = "analysis"
    HYPOTHESIS = "hypothesis"
    VALIDATION = "validation"
    CONCLUSION = "conclusion"
    EVIDENCE_GATHERING = "evidence_gathering"
    PATTERN_MATCHING = "pattern_matching"
    RISK_ASSESSMENT = "risk_assessment"

class ConfidenceLevel(Enum):
    """Confidence levels for reasoning steps"""
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9

@dataclass
class ReasoningStep:
    """Individual step in chain-of-thought reasoning"""
    step_id: str
    step_type: ReasoningStepType
    description: str
    input_data: Dict[str, Any]
    reasoning: str
    output: Dict[str, Any]
    confidence: float
    evidence: List[str]
    timestamp: str
    processing_time_ms: float
    dependencies: List[str] = None  # IDs of previous steps this depends on
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class ReasoningResult:
    """Complete reasoning result with all steps"""
    reasoning_id: str
    transaction_id: str
    steps: List[ReasoningStep]
    final_decision: Dict[str, Any]
    overall_confidence: float
    total_processing_time_ms: float
    reasoning_summary: str
    evidence_summary: List[str]
    timestamp: str
    model_used: str

class ChainOfThoughtReasoner:
    """
    Implements chain-of-thought reasoning for fraud detection
    Uses AWS Bedrock Claude models for advanced reasoning
    """
    
    def __init__(self, region_name: str = "us-east-1", model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """Initialize the reasoning engine"""
        self.region_name = region_name
        self.model_id = model_id
        self.bedrock_runtime = None
        self.reasoning_history: List[ReasoningResult] = []
        
        # Initialize AWS Bedrock Runtime client
        self._initialize_bedrock_client()
        
        # Reasoning templates
        self.reasoning_templates = self._load_reasoning_templates()
        
        logger.info(f"ChainOfThoughtReasoner initialized with model: {model_id}")
    
    def _initialize_bedrock_client(self):
        """Initialize AWS Bedrock Runtime client"""
        try:
            self.bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=self.region_name
            )
            logger.info("Bedrock Runtime client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def _load_reasoning_templates(self) -> Dict[str, str]:
        """Load reasoning prompt templates"""
        return {
            "fraud_analysis": """You are an expert fraud detection analyst. Analyze this transaction using step-by-step reasoning.

Transaction Details:
{transaction_data}

Context Information:
{context_data}

Please analyze this transaction using the following chain-of-thought approach:

1. OBSERVATION: What do you observe about this transaction?
2. PATTERN ANALYSIS: What patterns do you notice in the data?
3. RISK FACTORS: What risk factors are present?
4. HISTORICAL COMPARISON: How does this compare to typical patterns?
5. HYPOTHESIS: What is your initial hypothesis about fraud likelihood?
6. EVIDENCE GATHERING: What evidence supports or contradicts your hypothesis?
7. VALIDATION: How confident are you in your analysis?
8. CONCLUSION: What is your final assessment?

For each step, provide:
- Clear reasoning
- Specific evidence
- Confidence level (0.0-1.0)
- Key observations

Format your response as JSON with this structure:
{{
    "steps": [
        {{
            "step_type": "observation",
            "reasoning": "your reasoning here",
            "evidence": ["evidence item 1", "evidence item 2"],
            "confidence": 0.8,
            "key_findings": ["finding 1", "finding 2"]
        }}
    ],
    "final_assessment": {{
        "is_fraud": true/false,
        "confidence": 0.0-1.0,
        "risk_level": "LOW/MEDIUM/HIGH",
        "primary_concerns": ["concern 1", "concern 2"],
        "recommended_action": "APPROVE/FLAG/REVIEW/BLOCK"
    }}
}}""",
            
            "pattern_detection": """Analyze the following transaction for unusual patterns using systematic reasoning.

Transaction: {transaction_data}
User History: {user_history}
Similar Transactions: {similar_transactions}

Use this reasoning framework:

1. BASELINE ESTABLISHMENT: What is the user's normal behavior pattern?
2. DEVIATION ANALYSIS: How does this transaction deviate from the baseline?
3. TEMPORAL PATTERNS: Are there unusual timing patterns?
4. AMOUNT PATTERNS: Is the amount consistent with user behavior?
5. LOCATION PATTERNS: Are there geographic anomalies?
6. MERCHANT PATTERNS: Is this merchant typical for the user?
7. VELOCITY ANALYSIS: Is the transaction frequency unusual?
8. CORRELATION ANALYSIS: Do multiple factors correlate to suggest fraud?

Provide detailed reasoning for each step with evidence and confidence scores.""",
            
            "risk_assessment": """Perform a comprehensive risk assessment using multi-factor analysis.

Transaction: {transaction_data}
Risk Context: {risk_context}

Systematic risk evaluation:

1. INHERENT RISK: What are the base risk factors?
2. CONTEXTUAL RISK: How does context modify the risk?
3. BEHAVIORAL RISK: What behavioral indicators are present?
4. ENVIRONMENTAL RISK: What external factors affect risk?
5. CUMULATIVE RISK: How do all factors combine?
6. MITIGATION FACTORS: What factors reduce risk?
7. RISK QUANTIFICATION: What is the overall risk score?
8. RISK RECOMMENDATION: What action should be taken?

Provide numerical risk scores (0-100) for each category."""
        }
    
    def analyze_transaction_with_reasoning(self, transaction_data: Dict[str, Any], 
                                         context_data: Optional[Dict[str, Any]] = None) -> ReasoningResult:
        """
        Analyze a transaction using chain-of-thought reasoning
        """
        reasoning_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        logger.info(f"Starting chain-of-thought analysis for transaction: {transaction_data.get('id', 'unknown')}")
        
        try:
            # Prepare context
            if context_data is None:
                context_data = {}
            
            # Execute reasoning chain
            reasoning_steps = []
            
            # Step 1: Initial Observation
            observation_step = self._execute_reasoning_step(
                step_type=ReasoningStepType.OBSERVATION,
                description="Initial transaction observation and data gathering",
                input_data={"transaction": transaction_data, "context": context_data},
                prompt_template="fraud_analysis",
                dependencies=[]
            )
            reasoning_steps.append(observation_step)
            
            # Step 2: Pattern Analysis
            pattern_step = self._execute_reasoning_step(
                step_type=ReasoningStepType.PATTERN_MATCHING,
                description="Pattern detection and behavioral analysis",
                input_data={
                    "transaction": transaction_data,
                    "context": context_data,
                    "previous_findings": observation_step.output
                },
                prompt_template="pattern_detection",
                dependencies=[observation_step.step_id]
            )
            reasoning_steps.append(pattern_step)
            
            # Step 3: Risk Assessment
            risk_step = self._execute_reasoning_step(
                step_type=ReasoningStepType.RISK_ASSESSMENT,
                description="Comprehensive risk factor evaluation",
                input_data={
                    "transaction": transaction_data,
                    "context": context_data,
                    "observation_findings": observation_step.output,
                    "pattern_findings": pattern_step.output
                },
                prompt_template="risk_assessment",
                dependencies=[observation_step.step_id, pattern_step.step_id]
            )
            reasoning_steps.append(risk_step)
            
            # Step 4: Evidence Synthesis
            synthesis_step = self._synthesize_evidence(
                transaction_data=transaction_data,
                reasoning_steps=reasoning_steps
            )
            reasoning_steps.append(synthesis_step)
            
            # Step 5: Final Decision
            decision_step = self._make_final_decision(
                transaction_data=transaction_data,
                reasoning_steps=reasoning_steps
            )
            reasoning_steps.append(decision_step)
            
            # Calculate overall metrics
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            overall_confidence = self._calculate_overall_confidence(reasoning_steps)
            
            # Create final result
            reasoning_result = ReasoningResult(
                reasoning_id=reasoning_id,
                transaction_id=transaction_data.get('id', 'unknown'),
                steps=reasoning_steps,
                final_decision=decision_step.output,
                overall_confidence=overall_confidence,
                total_processing_time_ms=total_time,
                reasoning_summary=self._generate_reasoning_summary(reasoning_steps),
                evidence_summary=self._compile_evidence_summary(reasoning_steps),
                timestamp=datetime.now().isoformat(),
                model_used=self.model_id
            )
            
            # Store in history
            self.reasoning_history.append(reasoning_result)
            
            logger.info(f"Chain-of-thought analysis completed in {total_time:.2f}ms")
            return reasoning_result
            
        except Exception as e:
            logger.error(f"Chain-of-thought analysis failed: {str(e)}")
            raise
    
    def _execute_reasoning_step(self, step_type: ReasoningStepType, description: str,
                               input_data: Dict[str, Any], prompt_template: str,
                               dependencies: List[str]) -> ReasoningStep:
        """Execute a single reasoning step"""
        step_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        logger.debug(f"Executing reasoning step: {step_type.value}")
        
        try:
            # Prepare prompt
            if prompt_template in self.reasoning_templates:
                prompt = self.reasoning_templates[prompt_template].format(
                    transaction_data=json.dumps(input_data.get('transaction', {}), indent=2),
                    context_data=json.dumps(input_data.get('context', {}), indent=2),
                    user_history=json.dumps(input_data.get('user_history', []), indent=2),
                    similar_transactions=json.dumps(input_data.get('similar_transactions', []), indent=2),
                    risk_context=json.dumps(input_data.get('risk_context', {}), indent=2)
                )
            else:
                # Fallback generic prompt
                prompt = f"""Analyze the following data for fraud detection:

Data: {json.dumps(input_data, indent=2)}

Provide detailed reasoning and analysis."""
            
            # Call Bedrock model
            response = self._call_bedrock_model(prompt)
            
            # Parse response
            parsed_output = self._parse_reasoning_response(response, step_type)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create reasoning step
            reasoning_step = ReasoningStep(
                step_id=step_id,
                step_type=step_type,
                description=description,
                input_data=input_data,
                reasoning=parsed_output.get('reasoning', 'No reasoning provided'),
                output=parsed_output,
                confidence=parsed_output.get('confidence', 0.5),
                evidence=parsed_output.get('evidence', []),
                timestamp=datetime.now().isoformat(),
                processing_time_ms=processing_time,
                dependencies=dependencies
            )
            
            logger.debug(f"Reasoning step completed: {step_type.value} ({processing_time:.2f}ms)")
            return reasoning_step
            
        except Exception as e:
            logger.error(f"Reasoning step failed: {step_type.value} - {str(e)}")
            # Return error step
            return ReasoningStep(
                step_id=step_id,
                step_type=step_type,
                description=f"Failed: {description}",
                input_data=input_data,
                reasoning=f"Step failed due to error: {str(e)}",
                output={"error": str(e), "success": False},
                confidence=0.0,
                evidence=[f"Error: {str(e)}"],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                dependencies=dependencies
            )
    
    def _call_bedrock_model(self, prompt: str) -> str:
        """Call AWS Bedrock model for reasoning"""
        try:
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.1,  # Low temperature for consistent reasoning
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            else:
                raise ValueError("No content in model response")
                
        except Exception as e:
            logger.error(f"Bedrock model call failed: {str(e)}")
            # Return fallback response
            return json.dumps({
                "error": f"Model call failed: {str(e)}",
                "fallback_reasoning": "Unable to perform AI reasoning, using fallback logic",
                "confidence": 0.1
            })
    
    def _parse_reasoning_response(self, response: str, step_type: ReasoningStepType) -> Dict[str, Any]:
        """Parse the model's reasoning response"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                parsed = json.loads(response)
                return parsed
            
            # If not JSON, extract key information
            return {
                "reasoning": response,
                "confidence": 0.5,  # Default confidence
                "evidence": [response[:200] + "..." if len(response) > 200 else response],
                "step_type": step_type.value,
                "parsed_successfully": False
            }
            
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                "reasoning": response,
                "confidence": 0.3,
                "evidence": ["Raw model response"],
                "step_type": step_type.value,
                "parsing_error": True
            }
    
    def _synthesize_evidence(self, transaction_data: Dict[str, Any], 
                           reasoning_steps: List[ReasoningStep]) -> ReasoningStep:
        """Synthesize evidence from all previous reasoning steps"""
        step_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Collect all evidence
        all_evidence = []
        all_findings = []
        confidence_scores = []
        
        for step in reasoning_steps:
            all_evidence.extend(step.evidence)
            confidence_scores.append(step.confidence)
            if 'key_findings' in step.output:
                all_findings.extend(step.output['key_findings'])
        
        # Calculate weighted confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        # Create synthesis
        synthesis_output = {
            "evidence_count": len(all_evidence),
            "unique_evidence": list(set(all_evidence)),
            "key_findings": list(set(all_findings)),
            "confidence_distribution": confidence_scores,
            "average_confidence": avg_confidence,
            "synthesis_summary": f"Analyzed {len(reasoning_steps)} reasoning steps with {len(all_evidence)} pieces of evidence"
        }
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ReasoningStep(
            step_id=step_id,
            step_type=ReasoningStepType.EVIDENCE_GATHERING,
            description="Evidence synthesis from all reasoning steps",
            input_data={"previous_steps": len(reasoning_steps)},
            reasoning="Synthesized evidence from all previous reasoning steps to build comprehensive view",
            output=synthesis_output,
            confidence=avg_confidence,
            evidence=list(set(all_evidence)),
            timestamp=datetime.now().isoformat(),
            processing_time_ms=processing_time,
            dependencies=[step.step_id for step in reasoning_steps]
        )
    
    def _make_final_decision(self, transaction_data: Dict[str, Any], 
                           reasoning_steps: List[ReasoningStep]) -> ReasoningStep:
        """Make final fraud decision based on all reasoning steps"""
        step_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Analyze all steps for decision factors
        fraud_indicators = 0
        total_confidence = 0
        risk_factors = []
        
        for step in reasoning_steps:
            total_confidence += step.confidence
            
            # Look for fraud indicators in outputs
            if 'is_fraud' in step.output:
                if step.output['is_fraud']:
                    fraud_indicators += 1
            
            if 'risk_level' in step.output:
                if step.output['risk_level'] in ['HIGH', 'MEDIUM']:
                    fraud_indicators += 0.5
            
            if 'primary_concerns' in step.output:
                risk_factors.extend(step.output['primary_concerns'])
        
        # Calculate decision metrics
        avg_confidence = total_confidence / len(reasoning_steps) if reasoning_steps else 0.5
        fraud_probability = fraud_indicators / len(reasoning_steps) if reasoning_steps else 0.0
        
        # Make decision
        is_fraud = fraud_probability > 0.5
        risk_level = "HIGH" if fraud_probability > 0.7 else "MEDIUM" if fraud_probability > 0.3 else "LOW"
        
        # Determine action
        if is_fraud and avg_confidence > 0.8:
            action = "BLOCK"
        elif is_fraud and avg_confidence > 0.6:
            action = "REVIEW"
        elif fraud_probability > 0.3:
            action = "FLAG"
        else:
            action = "APPROVE"
        
        decision_output = {
            "is_fraud": is_fraud,
            "fraud_probability": fraud_probability,
            "confidence": avg_confidence,
            "risk_level": risk_level,
            "recommended_action": action,
            "risk_factors": list(set(risk_factors)),
            "decision_reasoning": f"Based on {len(reasoning_steps)} reasoning steps with {fraud_indicators} fraud indicators",
            "steps_analyzed": len(reasoning_steps)
        }
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ReasoningStep(
            step_id=step_id,
            step_type=ReasoningStepType.CONCLUSION,
            description="Final fraud decision based on comprehensive reasoning",
            input_data={"reasoning_steps_count": len(reasoning_steps)},
            reasoning=f"Final decision based on analysis of {len(reasoning_steps)} reasoning steps",
            output=decision_output,
            confidence=avg_confidence,
            evidence=[f"Fraud probability: {fraud_probability:.2f}", f"Risk level: {risk_level}"],
            timestamp=datetime.now().isoformat(),
            processing_time_ms=processing_time,
            dependencies=[step.step_id for step in reasoning_steps]
        )
    
    def _calculate_overall_confidence(self, reasoning_steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence from all reasoning steps"""
        if not reasoning_steps:
            return 0.0
        
        # Weight final decision step more heavily
        weights = []
        confidences = []
        
        for step in reasoning_steps:
            if step.step_type == ReasoningStepType.CONCLUSION:
                weights.append(0.4)  # 40% weight for final decision
            elif step.step_type == ReasoningStepType.EVIDENCE_GATHERING:
                weights.append(0.2)  # 20% weight for evidence synthesis
            else:
                weights.append(0.1)  # 10% weight for other steps
            
            confidences.append(step.confidence)
        
        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        # Calculate weighted average
        weighted_confidence = sum(c * w for c, w in zip(confidences, normalized_weights))
        
        return min(max(weighted_confidence, 0.0), 1.0)  # Clamp to [0, 1]
    
    def _generate_reasoning_summary(self, reasoning_steps: List[ReasoningStep]) -> str:
        """Generate human-readable summary of reasoning process"""
        if not reasoning_steps:
            return "No reasoning steps completed"
        
        summary_parts = []
        
        for i, step in enumerate(reasoning_steps, 1):
            step_summary = f"{i}. {step.step_type.value.title()}: {step.description}"
            if step.confidence > 0.7:
                step_summary += f" (High confidence: {step.confidence:.2f})"
            elif step.confidence < 0.3:
                step_summary += f" (Low confidence: {step.confidence:.2f})"
            
            summary_parts.append(step_summary)
        
        return "; ".join(summary_parts)
    
    def _compile_evidence_summary(self, reasoning_steps: List[ReasoningStep]) -> List[str]:
        """Compile all evidence from reasoning steps"""
        all_evidence = []
        
        for step in reasoning_steps:
            for evidence in step.evidence:
                if evidence not in all_evidence:
                    all_evidence.append(evidence)
        
        return all_evidence[:20]  # Limit to top 20 pieces of evidence
    
    def get_reasoning_history(self, limit: int = 10) -> List[ReasoningResult]:
        """Get recent reasoning history"""
        return self.reasoning_history[-limit:] if self.reasoning_history else []
    
    def get_reasoning_stats(self) -> Dict[str, Any]:
        """Get statistics about reasoning performance"""
        if not self.reasoning_history:
            return {"total_analyses": 0, "average_confidence": 0.0}
        
        total_analyses = len(self.reasoning_history)
        avg_confidence = sum(r.overall_confidence for r in self.reasoning_history) / total_analyses
        avg_processing_time = sum(r.total_processing_time_ms for r in self.reasoning_history) / total_analyses
        
        # Decision distribution
        decisions = [r.final_decision.get('recommended_action', 'UNKNOWN') for r in self.reasoning_history]
        decision_counts = {}
        for decision in decisions:
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        return {
            "total_analyses": total_analyses,
            "average_confidence": avg_confidence,
            "average_processing_time_ms": avg_processing_time,
            "decision_distribution": decision_counts,
            "model_used": self.model_id
        }

# Utility functions for testing and validation
def validate_reasoning_step(step: ReasoningStep) -> Dict[str, Any]:
    """Validate a reasoning step for completeness and quality"""
    validation_result = {
        "is_valid": True,
        "issues": [],
        "quality_score": 0.0
    }
    
    # Check required fields
    if not step.reasoning or len(step.reasoning) < 10:
        validation_result["issues"].append("Reasoning too short or missing")
        validation_result["is_valid"] = False
    
    if not step.evidence:
        validation_result["issues"].append("No evidence provided")
        validation_result["is_valid"] = False
    
    if step.confidence < 0.0 or step.confidence > 1.0:
        validation_result["issues"].append("Invalid confidence score")
        validation_result["is_valid"] = False
    
    # Calculate quality score
    quality_factors = []
    
    # Reasoning length (more detailed is better, up to a point)
    reasoning_length_score = min(len(step.reasoning) / 500, 1.0)
    quality_factors.append(reasoning_length_score)
    
    # Evidence count (more evidence is better, up to a point)
    evidence_count_score = min(len(step.evidence) / 5, 1.0)
    quality_factors.append(evidence_count_score)
    
    # Confidence appropriateness (not too high or too low)
    if 0.3 <= step.confidence <= 0.9:
        confidence_score = 1.0
    else:
        confidence_score = 0.5
    quality_factors.append(confidence_score)
    
    validation_result["quality_score"] = sum(quality_factors) / len(quality_factors)
    
    return validation_result