#!/usr/bin/env python3
"""
MVP Orchestrator Dry Run Testing
Tests the orchestrator script in dry-run mode to validate workflow logic
without making expensive API calls
"""

import asyncio
import json
import time
import yaml
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mvp_orchestrator_script import (
        MVPOrchestrator, Config, AIProvider, GateStatus,
        APIManager, DocumentManager, ProjectContext
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import orchestrator: {e}")
    ORCHESTRATOR_AVAILABLE = False

class MockAPIManager:
    """Mock API manager for dry-run testing"""
    
    def __init__(self, config):
        self.config = config
        self.total_costs = {provider: 0.0 for provider in AIProvider}
        self.call_count = 0
    
    async def call_api(self, provider: AIProvider, prompt: str, 
                      model: Optional[str] = None, max_tokens: int = 4000):
        """Mock API call that returns simulated content"""
        self.call_count += 1
        
        # Simulate different response types based on provider
        if provider == AIProvider.PERPLEXITY:
            content = f"""
# Market Research Analysis

## Market Size
The {prompt[:50]}... market is estimated at $2.1B with 15% YoY growth.

## Key Opportunities
1. Underserved SMB segment
2. AI automation demand increasing
3. Remote work trends driving adoption

## Competitive Landscape
- 5 major players control 60% market share
- 200+ startups in adjacent space
- Average funding: $2.3M seed rounds

## Revenue Models
- SaaS subscription: $29-99/month
- Usage-based pricing: $0.10 per API call
- Enterprise contracts: $50K+ annually
            """
            cost = self.config.perplexity_cost_per_request
            
        elif provider == AIProvider.ANTHROPIC:
            if "founder" in prompt.lower():
                content = f"""
# Founder-Market Fit Analysis

## Skill Alignment Score: 8.5/10
- Strong technical background matches market needs
- AI/ML experience highly relevant
- Previous startup experience valuable

## Recommendations
1. Focus on B2B segment initially
2. Leverage technical expertise for competitive advantage
3. Build MVP within 4-week timeline feasible

## Risk Assessment
- Low technical risk
- Medium market risk
- High execution opportunity
                """
            elif "specification" in prompt.lower() or "mvp" in prompt.lower():
                content = f"""
# MVP Specification

## Core Features
1. **User Authentication**
   - Email/password signup
   - OAuth integration
   - User profile management

2. **Content Generation**
   - AI-powered writing assistance
   - Template library
   - Real-time suggestions

3. **Document Management**
   - Save/load documents
   - Version control
   - Export formats

## Technical Architecture
- Frontend: React with TypeScript
- Backend: FastAPI with Python
- Database: PostgreSQL
- AI: OpenAI GPT-4 API

## Success Metrics
- 100+ active users in first month
- <2s response time for AI generation
- 90%+ user satisfaction score
                """
            else:
                content = f"""
# Architecture Design

## System Components
- API Gateway (FastAPI)
- Authentication Service
- Content Generation Service
- Database Layer (PostgreSQL)
- Caching Layer (Redis)

## Security Measures
- JWT token authentication
- Rate limiting
- Input validation
- SQL injection prevention

## Deployment Strategy
- Docker containerization
- AWS deployment
- Auto-scaling configuration
- Monitoring and alerting
                """
            
            # Simulate token usage for cost calculation
            input_tokens = len(prompt) // 4  # Rough estimate
            output_tokens = len(content) // 4
            cost = (input_tokens * self.config.anthropic_input_cost_per_1k / 1000 + 
                   output_tokens * self.config.anthropic_output_cost_per_1k / 1000)
            
        elif provider == AIProvider.OPENAI:
            content = f"""
# Generated Code

```python
# FastAPI backend structure
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

app = FastAPI(title="AI Writing Assistant")

@app.post("/generate")
async def generate_content(prompt: str, db: Session = Depends(get_db)):
    \"\"\"Generate AI-powered content\"\"\"
    try:
        # AI generation logic here
        result = await ai_service.generate(prompt)
        return {{"content": result, "status": "success"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {{"status": "healthy", "timestamp": datetime.now()}}
```

```javascript
// React frontend component
import React, { useState } from 'react';
import axios from 'axios';

const WritingAssistant = () => {{
  const [prompt, setPrompt] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);

  const generateContent = async () => {{
    setLoading(true);
    try {{
      const response = await axios.post('/api/generate', {{ prompt }});
      setContent(response.data.content);
    }} catch (error) {{
      console.error('Generation failed:', error);
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <div className="writing-assistant">
      <textarea 
        value={{prompt}}
        onChange={{(e) => setPrompt(e.target.value)}}
        placeholder="Enter your writing prompt..."
      />
      <button onClick={{generateContent}} disabled={{loading}}>
        {{loading ? 'Generating...' : 'Generate Content'}}
      </button>
      <div className="output">{{content}}</div>
    </div>
  );
}};

export default WritingAssistant;
```
            """
            # Simulate token usage
            input_tokens = len(prompt) // 4
            output_tokens = len(content) // 4  
            cost = (input_tokens * self.config.openai_input_cost_per_1k / 1000 +
                   output_tokens * self.config.openai_output_cost_per_1k / 1000)
        
        self.total_costs[provider] += cost
        
        # Add small delay to simulate API call
        await asyncio.sleep(0.1)
        
        return content, cost

class MockDocumentManager:
    """Mock document manager for dry-run testing"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.saved_docs = {}
    
    async def save_document(self, project_id: str, doc_type: str, content: str):
        """Mock document saving"""
        doc_key = f"{project_id}_{doc_type}"
        self.saved_docs[doc_key] = {
            "content": content,
            "timestamp": time.time(),
            "size": len(content)
        }
        
        # Create actual file for testing
        project_dir = self.project_root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{doc_type}_{timestamp}.md"
        filepath = project_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        return filepath
    
    async def load_document(self, filepath: Path):
        """Mock document loading"""
        if filepath.exists():
            with open(filepath, 'r') as f:
                return f.read()
        return ""
    
    async def list_documents(self, project_id: str, doc_type: Optional[str] = None):
        """Mock document listing"""
        project_dir = self.project_root / project_id
        if not project_dir.exists():
            return []
        
        pattern = f"{doc_type}_*.md" if doc_type else "*.md"
        return list(project_dir.glob(pattern))

class DryRunOrchestrator(MVPOrchestrator):
    """Orchestrator with mocked APIs for dry-run testing"""
    
    def __init__(self, config: Config, temp_dir: Path):
        # Initialize with mocked components
        self.config = config
        self.api_manager = MockAPIManager(config)
        self.doc_manager = MockDocumentManager(temp_dir / "documents")
        self.projects: Dict[str, ProjectContext] = {}
        self.temp_dir = temp_dir
        
    async def human_gate(self, gate_name: str, context: Dict[str, Any]) -> GateStatus:
        """Mock human gate that always approves for testing"""
        print(f"\n🚦 Mock Human Gate: {gate_name}")
        print(f"   📋 Context: {list(context.keys())}")
        
        # In dry-run mode, automatically approve all gates
        print("   ✅ Auto-approved for testing")
        return GateStatus.APPROVED

class OrchestratorDryRunTester:
    """Comprehensive dry-run testing for MVP orchestrator"""
    
    def __init__(self):
        self.temp_dir = None
        self.orchestrator = None
        self.test_results = []
        
    async def setup(self):
        """Setup test environment"""
        try:
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="orchestrator_dry_run_"))
            print(f"📂 Created temp directory: {self.temp_dir}")
            
            # Load configuration
            config_path = Path(__file__).parent / "config.yaml"
            if not config_path.exists():
                # Create minimal test config
                test_config = {
                    "openai_api_key": "sk-test-key",
                    "anthropic_api_key": "sk-ant-test-key", 
                    "perplexity_api_key": "pplx-test-key",
                    "project_root": str(self.temp_dir / "projects"),
                    "max_retries": 3,
                    "timeout": 30,
                    "use_perplexity_app": False,
                    "openai_input_cost_per_1k": 0.01,
                    "openai_output_cost_per_1k": 0.03,
                    "anthropic_input_cost_per_1k": 0.015,
                    "anthropic_output_cost_per_1k": 0.075,
                    "perplexity_cost_per_request": 0.005
                }
                
                with open(config_path, 'w') as f:
                    yaml.dump(test_config, f)
                print("📝 Created test configuration")
            
            # Load config and create orchestrator
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            config_data['project_root'] = str(self.temp_dir / "projects")
            config = Config(**config_data)
            
            self.orchestrator = DryRunOrchestrator(config, self.temp_dir)
            print("✅ Orchestrator initialized for dry-run testing")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup test environment"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def log_test_result(self, test_name: str, success: bool, details: str, 
                       duration: float = 0, cost: float = 0):
        """Log test result"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration": duration,
            "cost": cost,
            "timestamp": time.time()
        })
        
        icon = "✅" if success else "❌"
        print(f"{icon} {test_name}: {details}")
        if duration > 0:
            print(f"   ⏱️ Duration: {duration:.2f}s")
        if cost > 0:
            print(f"   💰 Cost: ${cost:.4f}")
    
    async def test_complete_workflow(self):
        """Test complete MVP development workflow"""
        print("\n🚀 Testing Complete MVP Workflow")
        
        start_time = time.time()
        
        try:
            # Test project creation
            project_id = await self.orchestrator.create_project(
                "AI Writing Assistant",
                "Content Creation", 
                "B2B SaaS"
            )
            
            # Test market research phase
            market_research = await self.orchestrator.run_market_research(
                "Content Creation",
                "B2B SaaS"
            )
            
            project = self.orchestrator.projects[project_id]
            project.market_research = market_research
            
            # Test founder analysis
            founder_analysis = await self.orchestrator.analyze_founder_fit(
                skills=["Python", "React", "AI/ML"],
                experience="5 years software development",
                market_opportunities=market_research["analysis"][:1000]
            )
            
            project.founder_analysis = founder_analysis
            
            # Test MVP specification
            mvp_spec = await self.orchestrator.generate_mvp_spec(
                problem="Content creators struggle with writer's block",
                solution="AI-powered writing assistant",
                target_users="Bloggers and marketers"
            )
            
            project.mvp_spec = mvp_spec
            
            # Test architecture design
            architecture = await self.orchestrator.create_architecture(
                mvp_spec["specification"],
                "React, FastAPI, PostgreSQL"
            )
            
            project.architecture = architecture
            
            # Test code generation
            code_result = await self.orchestrator.generate_code(
                "User authentication system",
                architecture["architecture"]
            )
            
            project.code_artifacts["auth_system"] = code_result
            
            # Save project
            await self.orchestrator.save_project(project_id)
            
            duration = time.time() - start_time
            total_cost = sum(self.orchestrator.api_manager.total_costs.values())
            
            # Validate results
            validation_checks = [
                market_research is not None,
                founder_analysis is not None,
                mvp_spec is not None,
                architecture is not None,
                code_result is not None,
                len(project.code_artifacts) > 0
            ]
            
            success = all(validation_checks)
            
            self.log_test_result(
                "Complete Workflow",
                success,
                f"Generated complete MVP project: {len(validation_checks)} phases completed",
                duration=duration,
                cost=total_cost
            )
            
            return success, project_id
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "Complete Workflow",
                False,
                f"Workflow failed: {str(e)}",
                duration=duration
            )
            return False, None
    
    async def test_project_generation(self, project_id: str):
        """Test project generation from orchestrator data"""
        print("\n🏗️ Testing Project Generation")
        
        start_time = time.time()
        
        try:
            if not project_id:
                raise ValueError("No project ID provided")
            
            # Test basic project generation (fallback)
            generation_result = await self.orchestrator._generate_basic_project(project_id)
            
            # Validate generated project
            project_path = Path(generation_result["project_path"])
            
            validation_checks = [
                project_path.exists(),
                (project_path / "README.md").exists(),
                generation_result["type"] == "basic",
                "timestamp" in generation_result
            ]
            
            success = all(validation_checks)
            duration = time.time() - start_time
            
            self.log_test_result(
                "Project Generation",
                success,
                f"Generated project at: {project_path}",
                duration=duration
            )
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "Project Generation",
                False,
                f"Project generation failed: {str(e)}",
                duration=duration
            )
            return False
    
    async def test_document_management(self, project_id: str):
        """Test document saving and retrieval"""
        print("\n📄 Testing Document Management")
        
        start_time = time.time()
        
        try:
            if not project_id:
                raise ValueError("No project ID provided")
            
            # Test document saving
            test_content = "# Test Document\n\nThis is a test document for validation."
            saved_path = await self.orchestrator.doc_manager.save_document(
                project_id,
                "test_doc",
                test_content
            )
            
            # Test document loading
            loaded_content = await self.orchestrator.doc_manager.load_document(saved_path)
            
            # Test document listing
            doc_list = await self.orchestrator.doc_manager.list_documents(project_id)
            
            validation_checks = [
                saved_path.exists(),
                loaded_content == test_content,
                len(doc_list) > 0,
                any("test_doc" in str(doc) for doc in doc_list)
            ]
            
            success = all(validation_checks)
            duration = time.time() - start_time
            
            self.log_test_result(
                "Document Management",
                success,
                f"Document operations successful: {len(doc_list)} documents",
                duration=duration
            )
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "Document Management",
                False,
                f"Document management failed: {str(e)}",
                duration=duration
            )
            return False
    
    async def test_cost_tracking(self):
        """Test cost tracking functionality"""
        print("\n💰 Testing Cost Tracking")
        
        start_time = time.time()
        
        try:
            # Check cost tracking data
            total_costs = self.orchestrator.api_manager.total_costs
            call_count = self.orchestrator.api_manager.call_count
            
            validation_checks = [
                isinstance(total_costs, dict),
                len(total_costs) == len(AIProvider),
                call_count > 0,
                sum(total_costs.values()) > 0
            ]
            
            success = all(validation_checks)
            duration = time.time() - start_time
            total_cost = sum(total_costs.values())
            
            self.log_test_result(
                "Cost Tracking",
                success,
                f"Tracked {call_count} API calls across {len(total_costs)} providers",
                duration=duration,
                cost=total_cost
            )
            
            # Print cost breakdown
            for provider, cost in total_costs.items():
                if cost > 0:
                    print(f"   💸 {provider.value}: ${cost:.4f}")
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "Cost Tracking",
                False,
                f"Cost tracking failed: {str(e)}",
                duration=duration
            )
            return False
    
    async def run_all_tests(self):
        """Run complete dry-run test suite"""
        print("🧪 Starting Orchestrator Dry-Run Testing Suite")
        print("=" * 60)
        
        if not await self.setup():
            print("❌ Setup failed, aborting tests")
            return False
        
        try:
            # Run workflow test
            workflow_success, project_id = await self.test_complete_workflow()
            
            # Run project generation test
            generation_success = await self.test_project_generation(project_id)
            
            # Run document management test
            docs_success = await self.test_document_management(project_id)
            
            # Run cost tracking test  
            cost_success = await self.test_cost_tracking()
            
            # Calculate overall results
            tests_passed = sum([
                workflow_success,
                generation_success,
                docs_success,
                cost_success
            ])
            
            total_tests = 4
            success_rate = tests_passed / total_tests
            
            print("\n" + "=" * 60)
            print("🏁 Dry-Run Testing Summary")
            print("=" * 60)
            print(f"✅ Tests Passed: {tests_passed}/{total_tests}")
            print(f"📊 Success Rate: {success_rate:.1%}")
            
            if tests_passed == total_tests:
                print("\n🎉 All dry-run tests passed! Orchestrator is working correctly.")
            elif success_rate >= 0.75:
                print(f"\n⚠️ Most tests passed but {total_tests - tests_passed} issues need attention.")
            else:
                print(f"\n❌ Multiple failures detected. Review implementation before proceeding.")
            
            # Generate report
            self.generate_report()
            
            return success_rate >= 0.75
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return False
        
        finally:
            self.cleanup()
    
    def generate_report(self):
        """Generate test report"""
        try:
            report_data = {
                "test_type": "orchestrator_dry_run",
                "timestamp": time.time(),
                "total_tests": len(self.test_results),
                "passed_tests": len([r for r in self.test_results if r["success"]]),
                "total_duration": sum(r["duration"] for r in self.test_results),
                "total_cost": sum(r["cost"] for r in self.test_results),
                "results": self.test_results
            }
            
            report_path = Path("orchestrator_dry_run_report.json")
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"📄 Test report saved to: {report_path}")
            
        except Exception as e:
            print(f"⚠️ Could not generate report: {e}")

async def main():
    """Main test execution"""
    if not ORCHESTRATOR_AVAILABLE:
        print("❌ MVP Orchestrator not available for testing")
        print("   Ensure mvp_orchestrator_script.py is importable")
        return False
    
    tester = OrchestratorDryRunTester()
    success = await tester.run_all_tests()
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)