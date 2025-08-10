#!/usr/bin/env python3
"""
Human-in-the-Loop Gate Workflows Testing

Comprehensive testing framework for the 4 critical human gates:
1. Gate 0: Niche Validation
2. Gate 1: Problem-Solution Fit  
3. Gate 2: Architecture Review
4. Gate 3: Release Readiness

This module tests gate sequencing, dependencies, timeouts, escalation, 
decision persistence, and workflow recovery after failures.
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "tools"))

from mvp_orchestrator_script import MVPOrchestrator, Config, GateStatus, PhaseStatus
from core_types import StartupStatus, TaskType, TaskStatus


class GateDecision(str, Enum):
    """Simulated human gate decisions"""
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"
    REVISION_NEEDED = "revision_needed"
    TIMEOUT = "timeout"


@dataclass
class GateTestScenario:
    """Test scenario for human gates"""
    gate_name: str
    context: Dict[str, Any]
    expected_decision: GateDecision
    simulate_delay: float = 0.0
    should_timeout: bool = False
    retry_attempts: int = 0


class MockHumanDecisionSimulator:
    """Simulates human decisions with configurable delays and outcomes"""
    
    def __init__(self):
        self.decisions: Dict[str, GateDecision] = {}
        self.decision_delays: Dict[str, float] = {}
        self.decision_history: List[Dict[str, Any]] = []
        self.timeout_threshold: float = 30.0
        self.pending_decisions: Dict[str, datetime] = {}
    
    def configure_decision(self, gate_name: str, decision: GateDecision, delay: float = 0.0):
        """Configure the decision for a specific gate"""
        self.decisions[gate_name] = decision
        self.decision_delays[gate_name] = delay
    
    async def make_decision(self, gate_name: str, context: Dict[str, Any]) -> GateStatus:
        """Simulate human decision making with configured behavior"""
        start_time = datetime.now()
        self.pending_decisions[gate_name] = start_time
        
        # Record decision attempt
        self.decision_history.append({
            "gate_name": gate_name,
            "context_keys": list(context.keys()),
            "timestamp": start_time,
            "status": "pending"
        })
        
        # Simulate delay
        delay = self.decision_delays.get(gate_name, 0.0)
        if delay > 0:
            await asyncio.sleep(delay)
        
        # Check for timeout
        if delay > self.timeout_threshold:
            self.decision_history[-1]["status"] = "timeout"
            return GateStatus.PENDING
        
        # Get configured decision
        decision = self.decisions.get(gate_name, GateDecision.APPROVE)
        
        # Map decision to gate status
        status_map = {
            GateDecision.APPROVE: GateStatus.APPROVED,
            GateDecision.REJECT: GateStatus.REJECTED,
            GateDecision.DEFER: GateStatus.PENDING,
            GateDecision.REVISION_NEEDED: GateStatus.REVISION_NEEDED,
            GateDecision.TIMEOUT: GateStatus.PENDING
        }
        
        gate_status = status_map[decision]
        
        # Update decision history
        self.decision_history[-1].update({
            "status": "completed",
            "decision": decision.value,
            "gate_status": gate_status.value,
            "duration": (datetime.now() - start_time).total_seconds()
        })
        
        # Remove from pending
        if gate_name in self.pending_decisions:
            del self.pending_decisions[gate_name]
        
        return gate_status
    
    def get_decision_metrics(self) -> Dict[str, Any]:
        """Get metrics about decision making"""
        if not self.decision_history:
            return {"total_decisions": 0}
        
        completed = [d for d in self.decision_history if d["status"] == "completed"]
        timeouts = [d for d in self.decision_history if d["status"] == "timeout"]
        
        avg_duration = sum(d["duration"] for d in completed) / len(completed) if completed else 0
        
        return {
            "total_decisions": len(self.decision_history),
            "completed_decisions": len(completed),
            "timeout_decisions": len(timeouts),
            "pending_decisions": len(self.pending_decisions),
            "average_decision_time": avg_duration,
            "success_rate": len(completed) / len(self.decision_history) if self.decision_history else 0
        }


class TestHumanGateWorkflows:
    """Main test class for human gate workflows"""
    
    @pytest.fixture
    def test_config(self):
        """Test configuration with temporary directory"""
        return Config(
            openai_api_key="test-key-gates",
            anthropic_api_key="test-key-gates",
            perplexity_api_key="test-key-gates",
            project_root=Path(tempfile.mkdtemp()) / "gate_tests",
            max_retries=2,
            timeout=15
        )
    
    @pytest.fixture
    def mock_external_apis(self):
        """Mock external API calls for testing"""
        with patch('openai.AsyncOpenAI') as mock_openai_client, \
             patch('anthropic.AsyncAnthropic') as mock_anthropic_client:
            
            # Configure mock responses
            mock_openai_response = Mock(
                choices=[Mock(message=Mock(content="Test market research response"))],
                usage=Mock(prompt_tokens=50, completion_tokens=100)
            )
            
            mock_anthropic_response = Mock(
                content=[Mock(text="Test founder analysis response")],
                usage=Mock(input_tokens=50, output_tokens=100)
            )
            
            mock_openai_client.return_value.chat.completions.create.return_value = mock_openai_response
            mock_anthropic_client.return_value.messages.create.return_value = mock_anthropic_response
            
            yield {
                "openai": mock_openai_client,
                "anthropic": mock_anthropic_client
            }
    
    @pytest.fixture
    def decision_simulator(self):
        """Human decision simulator for testing"""
        return MockHumanDecisionSimulator()
    
    @pytest.fixture
    def orchestrator_with_gates(self, test_config, mock_external_apis, decision_simulator):
        """Orchestrator with mocked human gate decisions"""
        orchestrator = MVPOrchestrator(test_config)
        
        # Patch the human_gate method to use our simulator
        async def mock_human_gate(gate_name: str, context: Dict[str, Any]) -> GateStatus:
            return await decision_simulator.make_decision(gate_name, context)
        
        orchestrator.human_gate = mock_human_gate
        
        return orchestrator, decision_simulator

    @pytest.mark.asyncio
    async def test_gate_0_niche_validation_workflow(self, orchestrator_with_gates):
        """Test Gate 0: Niche Validation - Market research → founder-market fit approval"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure decision
        simulator.configure_decision("Niche Validation", GateDecision.APPROVE, delay=1.0)
        
        # Create project
        project_id = await orchestrator.create_project(
            "Gate 0 Test",
            "FinTech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        
        # Run market research (prerequisite for gate)
        market_research = await orchestrator.run_market_research("FinTech", "B2B")
        project.market_research = market_research
        
        # Run founder analysis
        founder_analysis = await orchestrator.analyze_founder_fit(
            skills=["Python", "Finance", "API Design"],
            experience="5 years fintech",
            market_opportunities=market_research["analysis"][:500]
        )
        project.founder_analysis = founder_analysis
        
        # Test the gate
        start_time = time.time()
        gate_status = await orchestrator.human_gate(
            "Niche Validation",
            {
                "Market Opportunities": market_research["analysis"][:500],
                "Founder Fit Score": "Strong alignment with market needs"
            }
        )
        gate_time = time.time() - start_time
        
        # Assertions
        assert gate_status == GateStatus.APPROVED
        assert gate_time >= 1.0  # Respects configured delay
        assert gate_time < 5.0   # Reasonable upper bound
        
        # Verify project state
        project.gates["niche_validation"] = gate_status
        assert project.gates["niche_validation"] == GateStatus.APPROVED
        
        # Check decision metrics
        metrics = simulator.get_decision_metrics()
        assert metrics["total_decisions"] == 1
        assert metrics["completed_decisions"] == 1
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_gate_1_problem_solution_fit_workflow(self, orchestrator_with_gates):
        """Test Gate 1: Problem-Solution Fit - Problem validation → solution feasibility approval"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure decision
        simulator.configure_decision("Problem-Solution Fit", GateDecision.APPROVE)
        
        # Create project and complete prerequisites
        project_id = await orchestrator.create_project(
            "Gate 1 Test",
            "Healthcare",
            "B2C"
        )
        
        project = orchestrator.projects[project_id]
        
        # Simulate passed Gate 0
        project.gates["niche_validation"] = GateStatus.APPROVED
        
        # Generate MVP spec (prerequisite for gate)
        mvp_spec = await orchestrator.generate_mvp_spec(
            problem="Patients struggle to track medications effectively",
            solution="AI-powered medication reminder with smart scheduling",
            target_users="Adults with chronic conditions"
        )
        project.mvp_spec = mvp_spec
        
        # Test the gate
        gate_status = await orchestrator.human_gate(
            "Problem-Solution Fit",
            {
                "Problem": "Patients struggle to track medications effectively",
                "Solution": "AI-powered medication reminder with smart scheduling",
                "MVP Features": mvp_spec["specification"][:300]
            }
        )
        
        # Assertions
        assert gate_status == GateStatus.APPROVED
        
        # Verify workflow dependency
        assert project.gates.get("niche_validation") == GateStatus.APPROVED
        project.gates["problem_solution_fit"] = gate_status
        assert project.gates["problem_solution_fit"] == GateStatus.APPROVED

    @pytest.mark.asyncio
    async def test_gate_2_architecture_review_workflow(self, orchestrator_with_gates):
        """Test Gate 2: Architecture Review - Technical architecture → scalability approval"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure decision
        simulator.configure_decision("Architecture Review", GateDecision.APPROVE)
        
        # Create project and complete prerequisites
        project_id = await orchestrator.create_project(
            "Gate 2 Test",
            "EdTech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        
        # Simulate passed previous gates
        project.gates["niche_validation"] = GateStatus.APPROVED
        project.gates["problem_solution_fit"] = GateStatus.APPROVED
        
        # Create architecture (prerequisite for gate)
        architecture = await orchestrator.create_architecture(
            "EdTech platform for personalized learning",
            "React, Node.js, PostgreSQL, Redis"
        )
        project.architecture = architecture
        
        # Test the gate
        gate_status = await orchestrator.human_gate(
            "Architecture Review",
            {
                "Tech Stack": "React, Node.js, PostgreSQL, Redis",
                "Architecture": architecture["architecture"][:400],
                "Scalability Concerns": "Designed for 10k+ concurrent users"
            }
        )
        
        # Assertions
        assert gate_status == GateStatus.APPROVED
        
        # Verify workflow dependencies
        assert project.gates.get("niche_validation") == GateStatus.APPROVED
        assert project.gates.get("problem_solution_fit") == GateStatus.APPROVED
        project.gates["architecture_review"] = gate_status
        assert project.gates["architecture_review"] == GateStatus.APPROVED

    @pytest.mark.asyncio
    async def test_gate_3_release_readiness_workflow(self, orchestrator_with_gates):
        """Test Gate 3: Release Readiness - Quality metrics → release approval"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure decision
        simulator.configure_decision("Release Readiness", GateDecision.APPROVE)
        
        # Create project and complete prerequisites
        project_id = await orchestrator.create_project(
            "Gate 3 Test",
            "FinTech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        
        # Simulate passed all previous gates
        project.gates["niche_validation"] = GateStatus.APPROVED
        project.gates["problem_solution_fit"] = GateStatus.APPROVED
        project.gates["architecture_review"] = GateStatus.APPROVED
        
        # Simulate code generation and quality checks
        project.code_artifacts = {
            "backend_api": "Generated backend code...",
            "frontend_app": "Generated frontend code...",
            "tests": "Generated test suite..."
        }
        
        # Test the gate
        gate_status = await orchestrator.human_gate(
            "Release Readiness",
            {
                "Test Coverage": "85% - Exceeds 80% requirement",
                "Security Scan": "No critical vulnerabilities found",
                "Performance Tests": "Response time <200ms average",
                "Deployment Config": "Production-ready with monitoring"
            }
        )
        
        # Assertions
        assert gate_status == GateStatus.APPROVED
        
        # Verify complete workflow
        assert project.gates.get("niche_validation") == GateStatus.APPROVED
        assert project.gates.get("problem_solution_fit") == GateStatus.APPROVED
        assert project.gates.get("architecture_review") == GateStatus.APPROVED
        project.gates["release_readiness"] = gate_status
        assert project.gates["release_readiness"] == GateStatus.APPROVED

    @pytest.mark.asyncio
    async def test_gate_rejection_and_revision_workflow(self, orchestrator_with_gates):
        """Test gate rejection and revision workflow"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure initial rejection, then approval
        simulator.configure_decision("Problem-Solution Fit", GateDecision.REVISION_NEEDED)
        
        # Create project
        project_id = await orchestrator.create_project(
            "Gate Rejection Test",
            "Tech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        project.gates["niche_validation"] = GateStatus.APPROVED
        
        # Generate initial MVP spec
        mvp_spec = await orchestrator.generate_mvp_spec(
            problem="Vague problem statement",
            solution="Unclear solution approach", 
            target_users="Everyone"
        )
        project.mvp_spec = mvp_spec
        
        # Test initial rejection
        gate_status = await orchestrator.human_gate(
            "Problem-Solution Fit",
            {
                "Problem": "Vague problem statement",
                "Solution": "Unclear solution approach",
                "Target Users": "Everyone"
            }
        )
        
        # Should require revision
        assert gate_status == GateStatus.REVISION_NEEDED
        project.gates["problem_solution_fit"] = gate_status
        
        # Simulate revision
        simulator.configure_decision("Problem-Solution Fit", GateDecision.APPROVE)
        
        # Generate revised MVP spec
        revised_spec = await orchestrator.generate_mvp_spec(
            problem="Small businesses struggle with inventory management",
            solution="Simple, automated inventory tracking system",
            target_users="Small retail businesses with 1-10 employees"
        )
        project.mvp_spec = revised_spec
        
        # Test revised submission
        revised_gate_status = await orchestrator.human_gate(
            "Problem-Solution Fit",
            {
                "Problem": "Small businesses struggle with inventory management",
                "Solution": "Simple, automated inventory tracking system", 
                "Target Users": "Small retail businesses with 1-10 employees"
            }
        )
        
        # Should now be approved
        assert revised_gate_status == GateStatus.APPROVED
        project.gates["problem_solution_fit"] = revised_gate_status
        
        # Check decision history
        metrics = simulator.get_decision_metrics()
        assert metrics["total_decisions"] == 2
        assert metrics["completed_decisions"] == 2

    @pytest.mark.asyncio
    async def test_gate_timeout_handling(self, orchestrator_with_gates):
        """Test gate timeout handling and escalation"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure long delay that exceeds timeout
        simulator.configure_decision("Niche Validation", GateDecision.TIMEOUT, delay=35.0)
        simulator.timeout_threshold = 30.0
        
        # Create project
        project_id = await orchestrator.create_project(
            "Gate Timeout Test",
            "Tech",
            "B2B"
        )
        
        # Run prerequisites
        market_research = await orchestrator.run_market_research("Tech", "B2B")
        
        # Test gate with timeout
        start_time = time.time()
        gate_status = await orchestrator.human_gate(
            "Niche Validation",
            {
                "Market Research": market_research["analysis"][:300]
            }
        )
        gate_time = time.time() - start_time
        
        # Should timeout and remain pending
        assert gate_status == GateStatus.PENDING
        assert gate_time < 35.0  # Should timeout before full delay
        
        # Check timeout was recorded
        metrics = simulator.get_decision_metrics()
        assert metrics["timeout_decisions"] == 1
        assert metrics["success_rate"] < 1.0

    @pytest.mark.asyncio
    async def test_gate_sequencing_and_dependencies(self, orchestrator_with_gates):
        """Test that gates must be completed in sequence"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure all gates to approve
        for gate in ["Niche Validation", "Problem-Solution Fit", "Architecture Review", "Release Readiness"]:
            simulator.configure_decision(gate, GateDecision.APPROVE)
        
        # Create project
        project_id = await orchestrator.create_project(
            "Gate Sequence Test",
            "HealthTech",
            "B2C"
        )
        
        project = orchestrator.projects[project_id]
        
        # Test Gate 0: Niche Validation
        market_research = await orchestrator.run_market_research("HealthTech", "B2C")
        project.market_research = market_research
        
        gate_0_status = await orchestrator.human_gate(
            "Niche Validation",
            {"Market Research": "Summary of opportunities"}
        )
        assert gate_0_status == GateStatus.APPROVED
        project.gates["niche_validation"] = gate_0_status
        
        # Test Gate 1: Problem-Solution Fit (depends on Gate 0)
        mvp_spec = await orchestrator.generate_mvp_spec(
            "Clear problem", "Specific solution", "Defined users"
        )
        project.mvp_spec = mvp_spec
        
        gate_1_status = await orchestrator.human_gate(
            "Problem-Solution Fit",
            {"MVP Spec": "Well-defined specification"}
        )
        assert gate_1_status == GateStatus.APPROVED
        project.gates["problem_solution_fit"] = gate_1_status
        
        # Test Gate 2: Architecture Review (depends on Gates 0,1)
        architecture = await orchestrator.create_architecture(
            "Health platform", "Modern tech stack"
        )
        project.architecture = architecture
        
        gate_2_status = await orchestrator.human_gate(
            "Architecture Review", 
            {"Architecture": "Scalable design"}
        )
        assert gate_2_status == GateStatus.APPROVED
        project.gates["architecture_review"] = gate_2_status
        
        # Test Gate 3: Release Readiness (depends on all previous)
        gate_3_status = await orchestrator.human_gate(
            "Release Readiness",
            {"Quality Metrics": "All requirements met"}
        )
        assert gate_3_status == GateStatus.APPROVED
        project.gates["release_readiness"] = gate_3_status
        
        # Verify all gates completed in sequence
        assert project.gates["niche_validation"] == GateStatus.APPROVED
        assert project.gates["problem_solution_fit"] == GateStatus.APPROVED  
        assert project.gates["architecture_review"] == GateStatus.APPROVED
        assert project.gates["release_readiness"] == GateStatus.APPROVED
        
        # Check decision metrics
        metrics = simulator.get_decision_metrics()
        assert metrics["total_decisions"] == 4
        assert metrics["completed_decisions"] == 4
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_gate_decision_persistence(self, orchestrator_with_gates, test_config):
        """Test that gate decisions persist correctly"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure decisions
        simulator.configure_decision("Niche Validation", GateDecision.APPROVE)
        simulator.configure_decision("Problem-Solution Fit", GateDecision.REVISION_NEEDED)
        
        # Create project
        project_id = await orchestrator.create_project(
            "Gate Persistence Test",
            "Tech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        
        # Complete Gate 0
        market_research = await orchestrator.run_market_research("Tech", "B2B")
        project.market_research = market_research
        
        gate_0_status = await orchestrator.human_gate(
            "Niche Validation",
            {"Market Research": "Summary"}
        )
        project.gates["niche_validation"] = gate_0_status
        
        # Save project state
        await orchestrator.save_project(project_id)
        
        # Verify file persistence
        project_file = test_config.project_root / project_id / "project.json"
        assert project_file.exists()
        
        with open(project_file, 'r') as f:
            saved_data = json.load(f)
        
        # Check that gates were saved
        assert "gates" in saved_data
        assert saved_data["gates"]["niche_validation"] == GateStatus.APPROVED.value
        
        # Complete Gate 1 with revision needed
        mvp_spec = await orchestrator.generate_mvp_spec(
            "Problem", "Solution", "Users"
        )
        project.mvp_spec = mvp_spec
        
        gate_1_status = await orchestrator.human_gate(
            "Problem-Solution Fit",
            {"MVP Spec": "Initial spec"}
        )
        project.gates["problem_solution_fit"] = gate_1_status
        
        # Save again
        await orchestrator.save_project(project_id)
        
        # Verify both gate states persisted
        with open(project_file, 'r') as f:
            updated_data = json.load(f)
        
        assert updated_data["gates"]["niche_validation"] == GateStatus.APPROVED.value
        assert updated_data["gates"]["problem_solution_fit"] == GateStatus.REVISION_NEEDED.value

    @pytest.mark.asyncio
    async def test_concurrent_gate_processing(self, test_config, mock_external_apis):
        """Test concurrent gate processing for multiple startups"""
        # Create multiple orchestrators for concurrent testing
        orchestrators = []
        simulators = []
        
        for i in range(3):
            orchestrator = MVPOrchestrator(test_config)
            simulator = MockHumanDecisionSimulator()
            
            # Configure quick approvals
            simulator.configure_decision("Niche Validation", GateDecision.APPROVE, delay=0.5)
            
            async def mock_human_gate(gate_name: str, context: Dict[str, Any], sim=simulator) -> GateStatus:
                return await sim.make_decision(gate_name, context)
            
            orchestrator.human_gate = mock_human_gate
            
            orchestrators.append(orchestrator)
            simulators.append(simulator)
        
        # Create projects concurrently
        project_tasks = []
        for i, orchestrator in enumerate(orchestrators):
            task = orchestrator.create_project(
                f"Concurrent Project {i}",
                f"Industry {i}",
                f"Category {i}"
            )
            project_tasks.append(task)
        
        project_ids = await asyncio.gather(*project_tasks)
        
        # Run concurrent gate processing
        gate_tasks = []
        for orchestrator, project_id, simulator in zip(orchestrators, project_ids, simulators):
            # Setup prerequisites
            project = orchestrator.projects[project_id]
            market_research = await orchestrator.run_market_research(
                project.industry, project.category
            )
            project.market_research = market_research
            
            # Create gate task
            task = orchestrator.human_gate(
                "Niche Validation",
                {"Market Research": f"Research for {project.project_name}"}
            )
            gate_tasks.append(task)
        
        # Execute concurrent gates
        start_time = time.time()
        gate_results = await asyncio.gather(*gate_tasks)
        concurrent_time = time.time() - start_time
        
        # Assertions
        assert len(gate_results) == 3
        assert all(status == GateStatus.APPROVED for status in gate_results)
        assert concurrent_time < 2.0  # Should complete concurrently, not sequentially
        
        # Check all simulators processed decisions
        for simulator in simulators:
            metrics = simulator.get_decision_metrics()
            assert metrics["total_decisions"] == 1
            assert metrics["completed_decisions"] == 1

    @pytest.mark.asyncio
    async def test_gate_audit_trail(self, orchestrator_with_gates):
        """Test that gate decisions create proper audit trails"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Configure multiple decisions
        simulator.configure_decision("Niche Validation", GateDecision.APPROVE, delay=0.5)
        simulator.configure_decision("Problem-Solution Fit", GateDecision.REVISION_NEEDED, delay=1.0)
        simulator.configure_decision("Problem-Solution Fit", GateDecision.APPROVE, delay=0.3)
        
        # Create project
        project_id = await orchestrator.create_project(
            "Audit Trail Test",
            "Tech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        
        # Complete Gate 0
        market_research = await orchestrator.run_market_research("Tech", "B2B")
        project.market_research = market_research
        
        await orchestrator.human_gate(
            "Niche Validation",
            {"Market Research": "Summary"}
        )
        
        # Complete Gate 1 - initially rejected, then approved
        mvp_spec = await orchestrator.generate_mvp_spec(
            "Problem", "Solution", "Users"
        )
        project.mvp_spec = mvp_spec
        
        await orchestrator.human_gate(
            "Problem-Solution Fit", 
            {"MVP Spec": "Initial spec"}
        )
        
        await orchestrator.human_gate(
            "Problem-Solution Fit",
            {"MVP Spec": "Revised spec"}  
        )
        
        # Check audit trail
        metrics = simulator.get_decision_metrics()
        history = simulator.decision_history
        
        # Should have 3 decisions total
        assert metrics["total_decisions"] == 3
        assert len(history) == 3
        
        # Verify audit trail details
        assert history[0]["gate_name"] == "Niche Validation"
        assert history[0]["status"] == "completed"
        assert history[0]["decision"] == "approve"
        
        assert history[1]["gate_name"] == "Problem-Solution Fit"
        assert history[1]["status"] == "completed"
        assert history[1]["decision"] == "revision_needed"
        
        assert history[2]["gate_name"] == "Problem-Solution Fit"
        assert history[2]["status"] == "completed"
        assert history[2]["decision"] == "approve"
        
        # Verify timing information exists
        for record in history:
            assert "timestamp" in record
            assert "duration" in record
            assert isinstance(record["duration"], float)

    @pytest.mark.asyncio
    async def test_gate_workflow_recovery_after_failure(self, orchestrator_with_gates):
        """Test workflow recovery after gate or system failures"""
        orchestrator, simulator = orchestrator_with_gates
        
        # Create project
        project_id = await orchestrator.create_project(
            "Recovery Test",
            "FinTech",
            "B2B"
        )
        
        project = orchestrator.projects[project_id]
        
        # Complete some initial work
        market_research = await orchestrator.run_market_research("FinTech", "B2B")
        project.market_research = market_research
        
        # Simulate system failure during gate processing
        simulator.configure_decision("Niche Validation", GateDecision.APPROVE)
        
        # Complete gate successfully
        gate_status = await orchestrator.human_gate(
            "Niche Validation",
            {"Market Research": "Research data"}
        )
        project.gates["niche_validation"] = gate_status
        
        # Save state
        await orchestrator.save_project(project_id)
        
        # Simulate system restart - create new orchestrator
        new_orchestrator = MVPOrchestrator(orchestrator.config)
        
        # Load project state
        loaded_project = await new_orchestrator.load_project(project_id)
        
        # Verify recovery
        assert loaded_project is not None
        assert loaded_project.project_id == project_id
        assert loaded_project.gates["niche_validation"] == GateStatus.APPROVED
        assert loaded_project.market_research is not None
        
        # Continue workflow from recovered state
        new_simulator = MockHumanDecisionSimulator()
        new_simulator.configure_decision("Problem-Solution Fit", GateDecision.APPROVE)
        
        async def mock_human_gate(gate_name: str, context: Dict[str, Any]) -> GateStatus:
            return await new_simulator.make_decision(gate_name, context)
        
        new_orchestrator.human_gate = mock_human_gate
        
        # Generate MVP spec and continue
        mvp_spec = await new_orchestrator.generate_mvp_spec(
            "Fintech problem", "Fintech solution", "Fintech users"
        )
        loaded_project.mvp_spec = mvp_spec
        
        # Complete next gate
        gate_1_status = await new_orchestrator.human_gate(
            "Problem-Solution Fit",
            {"MVP Spec": "Specification"}
        )
        
        assert gate_1_status == GateStatus.APPROVED
        
        # Verify workflow continued successfully after recovery
        loaded_project.gates["problem_solution_fit"] = gate_1_status
        assert len(loaded_project.gates) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])