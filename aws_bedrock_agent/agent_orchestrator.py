#!/usr/bin/env python3
"""
AWS Bedrock Agent Orchestrator
Central coordinator for the fraud detection AI agent system
"""

import json
import logging
import boto3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PROCESSING = "processing"

@dataclass
class Transaction:
    """Enhanced transaction model for Bedrock Agent processing"""
    id: str
    user_id: str
    amount: float
    currency: str
    merchant: str
    category: str
    location: str
    timestamp: str
    card_type: str
    device_info: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class FraudDecision:
    """Fraud detection decision model"""
    transaction_id: str
    is_fraud: bool
    confidence_score: float
    risk_level: str
    reasoning: str
    evidence: List[str]
    recommended_action: str
    timestamp: str

@dataclass
class AnalysisRequest:
    """Request for transaction analysis"""
    transaction: Transaction
    priority: str = "normal"
    requested_agents: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class AgentResponse:
    """Response from specialized agents"""
    agent_id: str
    decision: FraudDecision
    processing_time: float
    tools_used: List[str]
    confidence: float
    status: AgentStatus

@dataclass
class WorkflowPlan:
    """Analysis workflow plan"""
    transaction_id: str
    steps: List[Dict[str, Any]]
    estimated_duration: float
    required_agents: List[str]
    priority: str

class AgentOrchestrator:
    """
    Central orchestrator for AWS Bedrock Agent-based fraud detection
    Coordinates multiple specialized agents and manages the overall workflow
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize the agent orchestrator"""
        self.region_name = region_name
        self.bedrock_agent_client = None
        self.bedrock_runtime_client = None
        self.active_agents = {}
        self.workflow_history = []
        
        # Initialize AWS clients
        self._initialize_aws_clients()
        
        # Agent configuration
        self.agent_config = {
            "transaction_analyzer": {
                "priority": 1,
                "timeout": 30,
                "required_tools": ["currency_converter", "merchant_validator"]
            },
            "pattern_detector": {
                "priority": 2,
                "timeout": 45,
                "required_tools": ["pattern_database", "anomaly_detector"]
            },
            "risk_assessor": {
                "priority": 1,
                "timeout": 30,
                "required_tools": ["geolocation_api", "risk_database"]
            },
            "compliance_checker": {
                "priority": 3,
                "timeout": 60,
                "required_tools": ["regulatory_database", "sanctions_list"]
            }
        }
        
        logger.info("AgentOrchestrator initialized successfully")
    
    def _initialize_aws_clients(self):
        """Initialize AWS Bedrock clients"""
        try:
            # Initialize Bedrock Agent client
            self.bedrock_agent_client = boto3.client(
                'bedrock-agent',
                region_name=self.region_name
            )
            
            # Initialize Bedrock Runtime client
            self.bedrock_runtime_client = boto3.client(
                'bedrock-agent-runtime',
                region_name=self.region_name
            )
            
            logger.info("AWS Bedrock clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise
    
    def process_transaction(self, transaction: Transaction) -> FraudDecision:
        """
        Main entry point for transaction processing
        Orchestrates the entire fraud detection workflow
        """
        logger.info(f"Processing transaction {transaction.id}")
        
        try:
            # Step 1: Plan the analysis workflow
            workflow_plan = self.plan_analysis_workflow(transaction)
            
            # Step 2: Create analysis request
            analysis_request = AnalysisRequest(
                transaction=transaction,
                priority=self._determine_priority(transaction),
                context=self._gather_context(transaction)
            )
            
            # Step 3: Coordinate agents
            agent_responses = self.coordinate_agents(analysis_request)
            
            # Step 4: Resolve conflicts and make final decision
            final_decision = self.resolve_conflicts(agent_responses)
            
            # Step 5: Log workflow completion
            self._log_workflow_completion(transaction.id, final_decision)
            
            return final_decision
            
        except Exception as e:
            logger.error(f"Error processing transaction {transaction.id}: {str(e)}")
            # Return safe default decision
            return self._create_error_decision(transaction, str(e))
    
    def coordinate_agents(self, analysis_request: AnalysisRequest) -> List[AgentResponse]:
        """
        Coordinate multiple specialized agents for transaction analysis
        """
        logger.info(f"Coordinating agents for transaction {analysis_request.transaction.id}")
        
        agent_responses = []
        
        # Determine which agents to invoke
        required_agents = self._select_agents(analysis_request)
        
        for agent_id in required_agents:
            try:
                # Invoke specialized agent
                response = self._invoke_agent(agent_id, analysis_request)
                agent_responses.append(response)
                
            except Exception as e:
                logger.error(f"Error invoking agent {agent_id}: {str(e)}")
                # Create error response
                error_response = self._create_error_response(agent_id, str(e))
                agent_responses.append(error_response)
        
        return agent_responses
    
    def resolve_conflicts(self, agent_responses: List[AgentResponse]) -> FraudDecision:
        """
        Resolve conflicts between agent decisions and create final decision
        """
        logger.info("Resolving conflicts between agent decisions")
        
        if not agent_responses:
            raise ValueError("No agent responses to resolve")
        
        # Extract decisions from responses
        decisions = [response.decision for response in agent_responses]
        
        # Weighted voting based on agent confidence and priority
        fraud_votes = []
        confidence_scores = []
        evidence_combined = []
        reasoning_parts = []
        
        for response in agent_responses:
            decision = response.decision
            agent_config = self.agent_config.get(response.agent_id, {})
            priority_weight = agent_config.get("priority", 1)
            
            # Weight the vote by confidence and priority
            weighted_vote = response.confidence * priority_weight
            fraud_votes.append(weighted_vote if decision.is_fraud else -weighted_vote)
            confidence_scores.append(response.confidence)
            evidence_combined.extend(decision.evidence)
            reasoning_parts.append(f"{response.agent_id}: {decision.reasoning}")
        
        # Calculate final decision
        final_fraud_score = sum(fraud_votes) / len(fraud_votes)
        is_fraud = final_fraud_score > 0
        final_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Determine risk level
        risk_level = self._calculate_risk_level(abs(final_fraud_score), final_confidence)
        
        # Create final decision
        final_decision = FraudDecision(
            transaction_id=decisions[0].transaction_id,
            is_fraud=is_fraud,
            confidence_score=final_confidence,
            risk_level=risk_level,
            reasoning=f"Multi-agent analysis: {'; '.join(reasoning_parts)}",
            evidence=list(set(evidence_combined)),  # Remove duplicates
            recommended_action=self._determine_action(is_fraud, risk_level, final_confidence),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Final decision: fraud={is_fraud}, confidence={final_confidence:.2f}")
        return final_decision
    
    def plan_analysis_workflow(self, transaction: Transaction) -> WorkflowPlan:
        """
        Plan the analysis workflow based on transaction characteristics
        """
        logger.info(f"Planning workflow for transaction {transaction.id}")
        
        # Analyze transaction to determine required steps
        steps = []
        required_agents = []
        estimated_duration = 0
        
        # Always include transaction analyzer
        steps.append({
            "step": "transaction_analysis",
            "agent": "transaction_analyzer",
            "estimated_time": 30
        })
        required_agents.append("transaction_analyzer")
        estimated_duration += 30
        
        # Add pattern detection for high-value transactions
        if transaction.amount > 1000:
            steps.append({
                "step": "pattern_detection",
                "agent": "pattern_detector",
                "estimated_time": 45
            })
            required_agents.append("pattern_detector")
            estimated_duration += 45
        
        # Add risk assessment for foreign transactions
        if transaction.location not in ["NEW_YORK_NY", "LOS_ANGELES_CA", "CHICAGO_IL"]:
            steps.append({
                "step": "risk_assessment",
                "agent": "risk_assessor",
                "estimated_time": 30
            })
            required_agents.append("risk_assessor")
            estimated_duration += 30
        
        # Add compliance check for high-risk scenarios
        if transaction.amount > 5000 or "HIGH_RISK" in transaction.location:
            steps.append({
                "step": "compliance_check",
                "agent": "compliance_checker",
                "estimated_time": 60
            })
            required_agents.append("compliance_checker")
            estimated_duration += 60
        
        # Determine priority
        priority = self._determine_priority(transaction)
        
        workflow_plan = WorkflowPlan(
            transaction_id=transaction.id,
            steps=steps,
            estimated_duration=estimated_duration,
            required_agents=required_agents,
            priority=priority
        )
        
        logger.info(f"Workflow planned: {len(steps)} steps, {estimated_duration}s estimated")
        return workflow_plan
    
    def _invoke_agent(self, agent_id: str, analysis_request: AnalysisRequest) -> AgentResponse:
        """
        Invoke a specialized agent using AWS Bedrock Agent Runtime
        """
        start_time = datetime.now()
        
        try:
            # Prepare the agent input
            agent_input = {
                "transaction": asdict(analysis_request.transaction),
                "context": analysis_request.context or {},
                "priority": analysis_request.priority
            }
            
            # For now, simulate agent invocation
            # In production, this would use actual Bedrock Agent Runtime
            decision = self._simulate_agent_decision(agent_id, analysis_request.transaction)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            response = AgentResponse(
                agent_id=agent_id,
                decision=decision,
                processing_time=processing_time,
                tools_used=self.agent_config[agent_id]["required_tools"],
                confidence=decision.confidence_score,
                status=AgentStatus.ACTIVE
            )
            
            logger.info(f"Agent {agent_id} completed in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {str(e)}")
            raise
    
    def _simulate_agent_decision(self, agent_id: str, transaction: Transaction) -> FraudDecision:
        """
        Simulate agent decision (placeholder for actual Bedrock Agent integration)
        """
        # This is a placeholder - in production, this would invoke actual Bedrock Agents
        
        if agent_id == "transaction_analyzer":
            is_fraud = transaction.amount > 10000 or "UNKNOWN" in transaction.merchant
            confidence = 0.85 if is_fraud else 0.75
            reasoning = f"Transaction analysis: amount=${transaction.amount}, merchant={transaction.merchant}"
            evidence = [f"Amount: ${transaction.amount}", f"Merchant: {transaction.merchant}"]
            
        elif agent_id == "pattern_detector":
            is_fraud = transaction.amount > 5000 and "FOREIGN" in transaction.location
            confidence = 0.80
            reasoning = "Pattern analysis detected unusual location-amount combination"
            evidence = [f"Location: {transaction.location}", f"Amount pattern anomaly"]
            
        elif agent_id == "risk_assessor":
            is_fraud = "HIGH_RISK" in transaction.location or transaction.currency != "USD"
            confidence = 0.70
            reasoning = f"Risk assessment based on location and currency"
            evidence = [f"Location risk: {transaction.location}", f"Currency: {transaction.currency}"]
            
        elif agent_id == "compliance_checker":
            is_fraud = transaction.amount > 10000  # AML threshold
            confidence = 0.90
            reasoning = "Compliance check for AML regulations"
            evidence = [f"AML threshold check: ${transaction.amount}"]
            
        else:
            is_fraud = False
            confidence = 0.50
            reasoning = "Unknown agent type"
            evidence = ["No analysis performed"]
        
        return FraudDecision(
            transaction_id=transaction.id,
            is_fraud=is_fraud,
            confidence_score=confidence,
            risk_level=self._calculate_risk_level(confidence, confidence),
            reasoning=reasoning,
            evidence=evidence,
            recommended_action="BLOCK" if is_fraud else "APPROVE",
            timestamp=datetime.now().isoformat()
        )
    
    def _select_agents(self, analysis_request: AnalysisRequest) -> List[str]:
        """Select appropriate agents based on transaction characteristics"""
        if analysis_request.requested_agents:
            return analysis_request.requested_agents
        
        # Default agent selection logic
        agents = ["transaction_analyzer"]
        
        transaction = analysis_request.transaction
        
        if transaction.amount > 1000:
            agents.append("pattern_detector")
        
        if transaction.location not in ["NEW_YORK_NY", "LOS_ANGELES_CA"]:
            agents.append("risk_assessor")
        
        if transaction.amount > 5000:
            agents.append("compliance_checker")
        
        return agents
    
    def _determine_priority(self, transaction: Transaction) -> str:
        """Determine transaction processing priority"""
        if transaction.amount > 10000:
            return "high"
        elif transaction.amount > 1000:
            return "medium"
        else:
            return "normal"
    
    def _gather_context(self, transaction: Transaction) -> Dict[str, Any]:
        """Gather additional context for transaction analysis"""
        return {
            "timestamp": datetime.now().isoformat(),
            "processing_mode": "real_time",
            "system_version": "1.0.0"
        }
    
    def _calculate_risk_level(self, score: float, confidence: float) -> str:
        """Calculate risk level based on score and confidence"""
        if score > 0.8 and confidence > 0.8:
            return "HIGH"
        elif score > 0.5 or confidence > 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _determine_action(self, is_fraud: bool, risk_level: str, confidence: float) -> str:
        """Determine recommended action based on decision"""
        if is_fraud and risk_level == "HIGH" and confidence > 0.8:
            return "BLOCK"
        elif is_fraud and risk_level in ["HIGH", "MEDIUM"]:
            return "REVIEW"
        elif is_fraud:
            return "FLAG"
        else:
            return "APPROVE"
    
    def _create_error_decision(self, transaction: Transaction, error_msg: str) -> FraudDecision:
        """Create error decision when processing fails"""
        return FraudDecision(
            transaction_id=transaction.id,
            is_fraud=True,  # Err on the side of caution
            confidence_score=0.0,
            risk_level="HIGH",
            reasoning=f"Processing error: {error_msg}",
            evidence=[f"System error: {error_msg}"],
            recommended_action="REVIEW",
            timestamp=datetime.now().isoformat()
        )
    
    def _create_error_response(self, agent_id: str, error_msg: str) -> AgentResponse:
        """Create error response when agent fails"""
        error_decision = FraudDecision(
            transaction_id="error",
            is_fraud=True,
            confidence_score=0.0,
            risk_level="HIGH",
            reasoning=f"Agent {agent_id} error: {error_msg}",
            evidence=[f"Agent error: {error_msg}"],
            recommended_action="REVIEW",
            timestamp=datetime.now().isoformat()
        )
        
        return AgentResponse(
            agent_id=agent_id,
            decision=error_decision,
            processing_time=0.0,
            tools_used=[],
            confidence=0.0,
            status=AgentStatus.ERROR
        )
    
    def _log_workflow_completion(self, transaction_id: str, decision: FraudDecision):
        """Log workflow completion for audit trail"""
        workflow_log = {
            "transaction_id": transaction_id,
            "completion_time": datetime.now().isoformat(),
            "final_decision": asdict(decision),
            "workflow_id": f"wf_{transaction_id}_{int(datetime.now().timestamp())}"
        }
        
        self.workflow_history.append(workflow_log)
        logger.info(f"Workflow completed for transaction {transaction_id}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all agents"""
        return {
            "orchestrator_status": "active",
            "active_agents": list(self.agent_config.keys()),
            "workflow_history_count": len(self.workflow_history),
            "last_updated": datetime.now().isoformat()
        }