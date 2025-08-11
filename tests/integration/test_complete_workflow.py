#!/usr/bin/env python3
"""
Integration Tests: Complete 8-Service Architecture Workflow
Tests the entire startup generation pipeline end-to-end.
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add core services to path
sys.path.append(str(Path(__file__).parent.parent.parent / "core"))

try:
    from conversation_service import ConversationService, BusinessBlueprint, BusinessModel, IndustryVertical
    from code_generation_service import CodeGenerationService, CodeArtifact
    from orchestration_service import OrchestrationService, WorkflowStage
    from deployment_service import DeploymentService, DeploymentConfig, CloudProvider
    from multi_tenant_service import MultiTenantService, ResourceLimits
    from ai_orchestration_service import AIOrchestrationService, AITask, TaskType, TaskPriority
    from observability_service import ObservabilityService, MetricType
    from integration_service import IntegrationService, SystemConfiguration, OperationMode
except ImportError as e:
    pytest.skip(f"Core services not available: {e}", allow_module_level=True)


class TestCompleteWorkflow:
    """Test complete startup generation workflow across all 8 services"""
    
    @pytest.fixture
    def mock_api_keys(self):
        """Mock API keys for testing"""
        return {
            "anthropic": "test-anthropic-key",
            "openai": "test-openai-key", 
            "perplexity": "test-perplexity-key"
        }
    
    @pytest.fixture
    def system_config(self, mock_api_keys):
        """Create system configuration for testing"""
        return SystemConfiguration(
            api_keys=mock_api_keys,
            max_concurrent_startups=5,
            default_resource_limits=ResourceLimits(
                memory_mb=256,
                cpu_cores=0.25,
                storage_gb=1,
                max_ports=3
            ),
            enable_monitoring=False,  # Disable for testing
            enable_multi_tenant=True,
            operation_mode=OperationMode.CLI
        )
    
    @pytest.fixture
    def mock_blueprint(self):
        """Create a mock business blueprint for testing"""
        return BusinessBlueprint(
            business_name="Test Healthcare Startup",
            description="AI-powered patient scheduling system",
            industry=IndustryVertical.HEALTHCARE,
            business_model=BusinessModel.B2B_SAAS,
            target_audience="Healthcare providers",
            key_features=["Appointment scheduling", "Patient management", "HIPAA compliance"],
            value_proposition="Reduce scheduling overhead by 50%",
            competitive_advantage="AI-powered optimization with HIPAA compliance",
            tech_stack_preferences={"backend": "fastapi", "frontend": "lit"},
            database_requirements=["Patient records", "Appointment slots", "Provider schedules"],
            integration_requirements=["EMR systems", "Payment processing"],
            compliance_requirements=["HIPAA", "HITECH"],
            monetization_strategy={"model": "subscription", "price_per_provider": 100},
            market_analysis={"market_size": "10B", "competitors": 5},
            user_personas=[{"name": "Dr. Smith", "role": "Primary care physician"}],
            created_at=time.time(),
            conversation_id="test_conversation_123",
            confidence_score=0.95
        )

    @pytest.mark.asyncio
    async def test_conversation_service_integration(self, mock_api_keys, mock_blueprint):
        """Test ConversationService generates valid business blueprints"""
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            # Mock Claude API response
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = """
            {
                "business_name": "Test Healthcare Startup",
                "problem_statement": "Healthcare scheduling is inefficient",
                "target_users": "Healthcare providers",
                "business_model": "b2b_saas",
                "industry": "healthcare",
                "confidence": 0.95
            }
            """
            
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            # Test conversation service
            conversation_service = ConversationService(mock_api_keys.get("anthropic"))
            
            # Mock the conversation flow (since real AI calls are expensive/slow)
            with patch.object(conversation_service, '_ai_conversation') as mock_conversation:
                mock_conversation.return_value = "Healthcare scheduling startup focused on providers"
                
                with patch.object(conversation_service, '_ai_structured_response') as mock_structured:
                    mock_structured.side_effect = [
                        {
                            "problem_statement": "Healthcare scheduling inefficiencies",
                            "target_users": "Healthcare providers", 
                            "business_model": "b2b_saas",
                            "industry": "healthcare",
                            "business_name": "Test Healthcare Startup",
                            "confidence": 0.95
                        },
                        {
                            "key_features": ["Appointment scheduling", "Patient management"],
                            "value_proposition": "Reduce scheduling overhead", 
                            "competitive_advantage": "AI-powered with HIPAA compliance",
                            "target_personas": [{"name": "Dr. Smith", "role": "physician"}],
                            "monetization": {"model": "subscription"},
                            "compliance_needs": ["HIPAA"]
                        },
                        {
                            "tech_stack": {"backend": "fastapi", "frontend": "lit"},
                            "database_schema": ["appointments", "patients"],
                            "integrations": ["EMR systems"]
                        }
                    ]
                    
                    # Execute conversation
                    blueprint = await conversation_service.conduct_founder_interview("test_session")
                    
                    # Validate blueprint structure
                    assert blueprint is not None
                    assert blueprint.business_name == "Test Healthcare Startup"
                    assert blueprint.industry == IndustryVertical.HEALTHCARE
                    assert blueprint.business_model == BusinessModel.B2B_SAAS
                    assert blueprint.confidence_score >= 0.8
                    assert len(blueprint.key_features) > 0
                    assert "HIPAA" in blueprint.compliance_requirements
    
    @pytest.mark.asyncio
    async def test_code_generation_service_integration(self, mock_api_keys, mock_blueprint):
        """Test CodeGenerationService generates valid code artifacts"""
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            # Mock Claude API responses for code generation
            mock_responses = [
                "# Database models for healthcare startup\nclass Patient(Base): pass",
                "# FastAPI endpoints\nfrom fastapi import FastAPI\napp = FastAPI()",
                "# Lit frontend components\nimport {LitElement} from 'lit'",
                "# Authentication system\ndef authenticate(): pass",
                "# Business logic\nclass SchedulingService: pass",
                "# Docker configuration\nFROM python:3.11",
                "# Documentation\n# Healthcare Startup MVP"
            ]
            
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = [
                MagicMock(content=[MagicMock(text=response)]) 
                for response in mock_responses
            ]
            mock_anthropic.return_value = mock_client
            
            # Test code generation
            code_service = CodeGenerationService(mock_api_keys.get("anthropic"))
            artifacts = await code_service.generate_complete_mvp(mock_blueprint)
            
            # Validate artifacts
            assert len(artifacts) >= 5  # Should generate multiple files
            assert any("models" in artifact.file_path for artifact in artifacts)
            assert any("main.py" in artifact.file_path for artifact in artifacts)
            assert any("component" in artifact.file_path for artifact in artifacts)
            
            # Validate healthcare-specific features
            healthcare_artifacts = [a for a in artifacts if "HIPAA" in a.content or "healthcare" in a.content.lower()]
            assert len(healthcare_artifacts) > 0, "Should include HIPAA/healthcare specific code"
            
            # Validate artifact structure
            for artifact in artifacts:
                assert artifact.file_path
                assert artifact.content
                assert artifact.artifact_type in ['backend', 'frontend', 'database', 'config', 'docs']
                assert artifact.size_lines > 0
    
    @pytest.mark.asyncio 
    async def test_multi_tenant_service_integration(self, mock_blueprint):
        """Test MultiTenantService properly isolates resources"""
        
        multi_tenant = MultiTenantService(max_concurrent_tenants=3)
        
        try:
            # Create multiple tenants
            tenant_ids = []
            for i in range(3):
                tenant_id = await multi_tenant.create_tenant(
                    business_name=f"Test Startup {i}",
                    founder_email=f"founder{i}@test.com",
                    resource_limits=ResourceLimits(
                        memory_mb=128,
                        cpu_cores=0.1,
                        storage_gb=0.5,
                        max_ports=2
                    )
                )
                tenant_ids.append(tenant_id)
            
            # Validate resource isolation
            for tenant_id in tenant_ids:
                tenant = multi_tenant.tenants[tenant_id]
                assert tenant.resource_allocation is not None
                assert tenant.resource_allocation.memory_mb == 128
                assert len(tenant.resource_allocation.allocated_ports) == 2
                
                # Update with blueprint
                await multi_tenant.update_tenant_blueprint(tenant_id, mock_blueprint)
                assert tenant.blueprint == mock_blueprint
            
            # Test resource conflicts - should fail when exceeding limits
            with pytest.raises(Exception, match="Maximum.*tenants"):
                await multi_tenant.create_tenant(
                    "Overflow Startup",
                    "overflow@test.com"
                )
            
            # Test port isolation - no overlapping ports
            all_ports = []
            for tenant_id in tenant_ids:
                tenant = multi_tenant.tenants[tenant_id]
                all_ports.extend(tenant.resource_allocation.allocated_ports)
            
            assert len(all_ports) == len(set(all_ports)), "Ports should be unique across tenants"
            
            # Test cost tracking
            for tenant_id in tenant_ids:
                cost_data = await multi_tenant.track_tenant_costs(tenant_id)
                assert "total_cost" in cost_data
                assert cost_data["total_cost"] >= 0
                assert "within_budget" in cost_data
            
            # Test system overview
            overview = multi_tenant.get_system_overview()
            assert overview["active_tenants"] == 3
            assert overview["total_tenants"] == 3
            assert overview["resource_utilization"]["memory_utilization"] > 0
            
        finally:
            # Cleanup
            for tenant_id in tenant_ids:
                await multi_tenant.deallocate_resources(tenant_id)
    
    @pytest.mark.asyncio
    async def test_observability_service_integration(self):
        """Test ObservabilityService monitoring and metrics"""
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            obs_service = ObservabilityService(db_path=tmp_db.name)
            
            try:
                # Test metric recording
                obs_service.record_metric("startup_creation_time", 23.5, MetricType.TIMER)
                obs_service.record_metric("active_tenants", 3, MetricType.GAUGE)
                obs_service.record_metric("api_calls", 1, MetricType.COUNTER)
                
                # Test business metrics
                obs_service.update_business_metrics(
                    startups_created_today=2,
                    startups_created_total=15,
                    successful_deployments=14,
                    deployment_success_rate=93.3
                )
                
                # Test alert system
                obs_service.trigger_alert(
                    "test_alert",
                    "Test alert message",
                    obs_service.AlertSeverity.WARNING
                )
                
                assert len(obs_service.active_alerts) == 1
                
                # Test health checks
                health = await obs_service.get_system_health()
                assert "overall_status" in health
                assert "health_checks" in health
                assert "active_alerts" in health
                assert health["active_alerts"] == 1
                
                # Test metrics summary
                summary = obs_service.get_metrics_summary(hours=1)
                assert "system_metrics" in summary
                assert "business_metrics" in summary
                
            finally:
                obs_service.stop_monitoring()
                os.unlink(tmp_db.name)
    
    @pytest.mark.asyncio
    async def test_integration_service_workflow(self, system_config, mock_blueprint):
        """Test IntegrationService coordinates all services properly"""
        
        # Mock external dependencies to avoid real API calls
        with patch('core.conversation_service.ConversationService') as mock_conversation, \
             patch('core.code_generation_service.CodeGenerationService') as mock_codegen, \
             patch('core.deployment_service.DeploymentService') as mock_deployment:
            
            # Setup mocks
            mock_conversation_instance = AsyncMock()
            mock_conversation_instance.conduct_founder_interview.return_value = mock_blueprint
            mock_conversation.return_value = mock_conversation_instance
            
            mock_codegen_instance = AsyncMock()
            mock_artifacts = [
                CodeArtifact("backend/main.py", "# FastAPI app", "backend", "fastapi", 10, time.time()),
                CodeArtifact("frontend/app.ts", "// Lit component", "frontend", "lit", 5, time.time())
            ]
            mock_codegen_instance.generate_complete_mvp.return_value = mock_artifacts
            mock_codegen.return_value = mock_codegen_instance
            
            mock_deployment_instance = AsyncMock()
            mock_deployment_result = MagicMock()
            mock_deployment_result.success = True
            mock_deployment_result.urls = {
                "frontend_url": "http://localhost:3000",
                "api_url": "http://localhost:8000"
            }
            mock_deployment_result.deployment_id = "test_deployment_123"
            mock_deployment_instance.deploy_complete_mvp.return_value = mock_deployment_result
            mock_deployment.return_value = mock_deployment_instance
            
            # Test integration service workflow
            integration_service = IntegrationService(system_config)
            
            session = await integration_service.start_complete_workflow(
                business_name="Test Healthcare Startup",
                founder_email="founder@test.com"
            )
            
            # Validate session results
            assert session is not None
            assert session.status == "completed"
            assert session.blueprint == mock_blueprint
            assert len(session.artifacts) == 2
            assert session.deployment_result is not None
            assert session.deployment_result["success"] is True
            assert "frontend_url" in session.deployment_result["urls"]
            
            # Validate service calls were made
            mock_conversation_instance.conduct_founder_interview.assert_called_once()
            mock_codegen_instance.generate_complete_mvp.assert_called_once_with(mock_blueprint)
            mock_deployment_instance.deploy_complete_mvp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_resilience(self, system_config):
        """Test system handles errors gracefully without cascade failures"""
        
        # Test conversation service failure
        with patch('core.conversation_service.ConversationService') as mock_conversation:
            mock_conversation_instance = AsyncMock()
            mock_conversation_instance.conduct_founder_interview.side_effect = Exception("API failure")
            mock_conversation.return_value = mock_conversation_instance
            
            integration_service = IntegrationService(system_config)
            
            # Should handle the error gracefully
            with pytest.raises(Exception):
                await integration_service.start_complete_workflow(
                    "Test Startup",
                    "founder@test.com"
                )
            
            # System should still be in a valid state
            overview = await integration_service.get_system_overview()
            assert overview is not None
    
    @pytest.mark.asyncio
    async def test_performance_targets(self, system_config, mock_blueprint):
        """Test system meets performance targets"""
        
        with patch('core.conversation_service.ConversationService') as mock_conversation, \
             patch('core.code_generation_service.CodeGenerationService') as mock_codegen, \
             patch('core.deployment_service.DeploymentService') as mock_deployment:
            
            # Setup fast mocks to test performance
            mock_conversation_instance = AsyncMock()
            mock_conversation_instance.conduct_founder_interview.return_value = mock_blueprint
            mock_conversation.return_value = mock_conversation_instance
            
            mock_codegen_instance = AsyncMock() 
            mock_codegen_instance.generate_complete_mvp.return_value = []
            mock_codegen.return_value = mock_codegen_instance
            
            mock_deployment_instance = AsyncMock()
            mock_deployment_result = MagicMock()
            mock_deployment_result.success = True
            mock_deployment_result.urls = {}
            mock_deployment_result.deployment_id = "test"
            mock_deployment_instance.deploy_complete_mvp.return_value = mock_deployment_result
            mock_deployment.return_value = mock_deployment_instance
            
            # Measure workflow performance
            start_time = time.time()
            
            integration_service = IntegrationService(system_config)
            session = await integration_service.start_complete_workflow(
                "Performance Test Startup",
                "perf@test.com"
            )
            
            end_time = time.time()
            workflow_time = end_time - start_time
            
            # Performance targets (for mocked workflow)
            assert workflow_time < 5.0, f"Workflow took {workflow_time:.2f}s, should be < 5s with mocks"
            assert session.status == "completed"


class TestServiceCommunication:
    """Test inter-service communication and contracts"""
    
    @pytest.mark.asyncio
    async def test_service_contracts_maintained(self):
        """Test that service interfaces remain consistent"""
        
        # Test ConversationService contract
        conversation_service = ConversationService()
        assert hasattr(conversation_service, 'conduct_founder_interview')
        assert hasattr(conversation_service, 'save_blueprint')
        
        # Test CodeGenerationService contract
        code_service = CodeGenerationService()
        assert hasattr(code_service, 'generate_complete_mvp')
        assert hasattr(code_service, 'get_generation_summary')
        
        # Test MultiTenantService contract
        multi_tenant = MultiTenantService()
        assert hasattr(multi_tenant, 'create_tenant')
        assert hasattr(multi_tenant, 'deallocate_resources')
        assert hasattr(multi_tenant, 'track_tenant_costs')
        
        # Test ObservabilityService contract
        obs_service = ObservabilityService()
        assert hasattr(obs_service, 'record_metric')
        assert hasattr(obs_service, 'trigger_alert')
        assert hasattr(obs_service, 'get_system_health')
    
    def test_data_models_consistent(self):
        """Test that data models are properly structured"""
        from datetime import datetime
        
        # Test BusinessBlueprint model
        blueprint = BusinessBlueprint(
            business_name="Test",
            description="Test description", 
            industry=IndustryVertical.TECHNOLOGY,
            business_model=BusinessModel.B2B_SAAS,
            target_audience="Developers",
            key_features=["Feature 1"],
            value_proposition="Test value",
            competitive_advantage="Test advantage",
            tech_stack_preferences={},
            database_requirements=[],
            integration_requirements=[], 
            compliance_requirements=[],
            monetization_strategy={},
            market_analysis={},
            user_personas=[],
            created_at=datetime.now(),
            conversation_id="test",
            confidence_score=0.8
        )
        
        assert blueprint.business_name == "Test"
        assert blueprint.industry == IndustryVertical.TECHNOLOGY
        assert blueprint.confidence_score == 0.8
        
        # Test blueprint serialization
        blueprint_dict = blueprint.to_dict()
        assert isinstance(blueprint_dict, dict)
        assert "business_name" in blueprint_dict
        
        # Test blueprint deserialization
        restored_blueprint = BusinessBlueprint.from_dict(blueprint_dict)
        assert restored_blueprint.business_name == blueprint.business_name


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])