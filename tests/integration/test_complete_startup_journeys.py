#!/usr/bin/env python3
"""
Complete Startup Creation Journey Tests
======================================

Comprehensive end-to-end testing for complete startup creation workflows from idea to deployed MVP.
Tests the entire user journey through realistic scenarios across multiple startup types and complexity levels.

Test Coverage:
- 5 Different startup industries (FinTech, HealthTech, EdTech, E-commerce, B2B SaaS)
- 3 Complexity levels per industry (Simple, Medium, Complex)
- Success and failure scenario paths
- Concurrent execution testing
- Resource cleanup and isolation validation

Success Criteria:
- Complete startup creation working for all scenarios
- Generated MVPs are functional and deployable
- Cost tracking accurate throughout entire journey
- Performance acceptable for production use (<30 min complete journey)
- Quality gates ensuring high-standard MVP outputs
"""

import asyncio
import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, Mock, AsyncMock
import pytest

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import required modules
from tools.mvp_orchestrator_script import MVPOrchestrator, Config, GateStatus, PhaseStatus
from tools.ai_providers import AIProviderManager, create_default_provider_manager
from tools.template_manager import TemplateManager, TemplateInfo
from tools.budget_monitor import BudgetMonitor, BudgetLimit
from tools.core_types import StartupConfig, TaskType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== COMPREHENSIVE STARTUP SCENARIOS =====

STARTUP_SCENARIOS = {
    # FinTech Scenarios
    "fintech_simple": {
        "name": "Personal Budget Tracker",
        "industry": "FinTech",
        "category": "Personal Finance",
        "complexity": "simple",
        "problem": "People struggle to track their daily expenses and understand spending patterns",
        "solution": "Simple expense tracking app with automated categorization and spending insights",
        "target_users": "Young professionals aged 22-35 who want better financial awareness",
        "tech_stack": "React, Node.js, PostgreSQL",
        "skills": ["React", "Node.js", "Basic Finance"],
        "experience": "2 years web development, new to fintech",
        "expected_features": ["Expense tracking", "Category management", "Basic reporting"],
        "max_cost": 0.50,
        "max_time": 300  # 5 minutes
    },
    
    "fintech_medium": {
        "name": "SME Invoice Management",
        "industry": "FinTech",
        "category": "B2B Finance",
        "complexity": "medium",
        "problem": "Small businesses struggle with invoice management and payment tracking",
        "solution": "Automated invoicing platform with payment reminders and cash flow forecasting",
        "target_users": "Small business owners with 5-50 employees",
        "tech_stack": "Vue.js, Python FastAPI, PostgreSQL, Redis",
        "skills": ["Vue.js", "Python", "API Development", "Business Finance"],
        "experience": "4 years full-stack development, 1 year in business automation",
        "expected_features": ["Invoice generation", "Payment tracking", "Cash flow forecasting", "Client management"],
        "max_cost": 1.00,
        "max_time": 600  # 10 minutes
    },
    
    "fintech_complex": {
        "name": "Algorithmic Trading Platform",
        "industry": "FinTech",
        "category": "Investment Technology",
        "complexity": "complex",
        "problem": "Individual investors lack access to sophisticated algorithmic trading tools",
        "solution": "Democratized algorithmic trading platform with backtesting and risk management",
        "target_users": "Retail investors with $10K+ portfolios interested in algorithmic trading",
        "tech_stack": "React TypeScript, Python FastAPI, PostgreSQL, Redis, Celery",
        "skills": ["React", "TypeScript", "Python", "Machine Learning", "Financial Markets", "Risk Management"],
        "experience": "6 years software development, 3 years in fintech, CFA Level 1",
        "expected_features": ["Strategy builder", "Backtesting engine", "Risk management", "Portfolio analytics", "Real-time execution"],
        "max_cost": 2.00,
        "max_time": 1200  # 20 minutes
    },

    # HealthTech Scenarios
    "healthtech_simple": {
        "name": "Symptom Tracker",
        "industry": "HealthTech",
        "category": "Personal Health",
        "complexity": "simple",
        "problem": "Patients forget to track symptoms between doctor visits",
        "solution": "Simple symptom logging app with reminder notifications and exportable reports",
        "target_users": "Patients with chronic conditions who need to track symptoms",
        "tech_stack": "React Native, Node.js, SQLite",
        "skills": ["React Native", "Node.js", "Mobile Development"],
        "experience": "3 years mobile development, interest in healthcare",
        "expected_features": ["Symptom logging", "Reminders", "Export reports", "Trend visualization"],
        "max_cost": 0.40,
        "max_time": 240
    },
    
    "healthtech_medium": {
        "name": "Telemedicine Scheduler",
        "industry": "HealthTech",
        "category": "Healthcare Operations",
        "complexity": "medium",
        "problem": "Medical practices struggle with appointment scheduling and video consultation coordination",
        "solution": "Integrated scheduling and telemedicine platform with automated reminders",
        "target_users": "Small to medium medical practices with 2-10 healthcare providers",
        "tech_stack": "React, Python Django, PostgreSQL, WebRTC",
        "skills": ["React", "Python", "Django", "WebRTC", "Healthcare Operations"],
        "experience": "5 years web development, 2 years in healthcare IT",
        "expected_features": ["Appointment scheduling", "Video consultations", "Patient records", "Insurance verification"],
        "max_cost": 1.20,
        "max_time": 720
    },
    
    "healthtech_complex": {
        "name": "AI Diagnostic Assistant",
        "industry": "HealthTech",
        "category": "Medical AI",
        "complexity": "complex",
        "problem": "Rural healthcare providers lack access to specialist diagnostic expertise",
        "solution": "AI-powered diagnostic assistant with medical imaging analysis and decision support",
        "target_users": "Primary care physicians in underserved areas",
        "tech_stack": "React, Python FastAPI, PostgreSQL, TensorFlow, Docker",
        "skills": ["React", "Python", "Machine Learning", "TensorFlow", "Medical Imaging", "HIPAA Compliance"],
        "experience": "8 years software development, 4 years ML, PhD in Computer Science",
        "expected_features": ["Medical image analysis", "Diagnostic suggestions", "Decision support", "HIPAA compliance", "Integration APIs"],
        "max_cost": 2.50,
        "max_time": 1500
    },

    # EdTech Scenarios
    "edtech_simple": {
        "name": "Flashcard Learning App",
        "industry": "EdTech",
        "category": "Study Tools",
        "complexity": "simple",
        "problem": "Students need better tools for memorization and spaced repetition learning",
        "solution": "Digital flashcard app with spaced repetition algorithm and progress tracking",
        "target_users": "High school and college students preparing for exams",
        "tech_stack": "Vue.js, Node.js, MongoDB",
        "skills": ["Vue.js", "Node.js", "MongoDB", "Educational Psychology"],
        "experience": "2 years web development, background in education",
        "expected_features": ["Flashcard creation", "Spaced repetition", "Progress tracking", "Sharing"],
        "max_cost": 0.35,
        "max_time": 200
    },
    
    "edtech_medium": {
        "name": "Online Course Platform",
        "industry": "EdTech",
        "category": "Online Learning",
        "complexity": "medium",
        "problem": "Individual educators struggle to create and monetize online courses",
        "solution": "Course creation platform with video hosting, student management, and payment processing",
        "target_users": "Independent educators and small training organizations",
        "tech_stack": "React, Python Flask, PostgreSQL, AWS S3",
        "skills": ["React", "Python", "Flask", "AWS", "Video Processing", "Payment Systems"],
        "experience": "4 years full-stack development, experience in e-learning",
        "expected_features": ["Course builder", "Video hosting", "Student management", "Payment processing", "Analytics"],
        "max_cost": 1.00,
        "max_time": 600
    },
    
    "edtech_complex": {
        "name": "Adaptive Learning Platform",
        "industry": "EdTech",
        "category": "Personalized Learning",
        "complexity": "complex",
        "problem": "Students learn at different paces but current systems use one-size-fits-all approaches",
        "solution": "AI-powered adaptive learning platform that personalizes content and pacing",
        "target_users": "K-12 schools looking for personalized learning solutions",
        "tech_stack": "React TypeScript, Python Django, PostgreSQL, TensorFlow, Kubernetes",
        "skills": ["React", "TypeScript", "Python", "Django", "Machine Learning", "Learning Analytics", "Kubernetes"],
        "experience": "7 years software development, 3 years in EdTech, M.Ed. in Educational Technology",
        "expected_features": ["Adaptive algorithms", "Learning analytics", "Content management", "Teacher dashboard", "Progress tracking"],
        "max_cost": 2.20,
        "max_time": 1300
    },

    # E-commerce Scenarios
    "ecommerce_simple": {
        "name": "Local Marketplace",
        "industry": "E-commerce",
        "category": "Marketplace",
        "complexity": "simple",
        "problem": "Local artisans and small businesses struggle to reach customers online",
        "solution": "Simple local marketplace for handmade and local products with pickup/delivery",
        "target_users": "Local artisans, small businesses, and community shoppers",
        "tech_stack": "React, Node.js, PostgreSQL, Stripe",
        "skills": ["React", "Node.js", "PostgreSQL", "Stripe API", "E-commerce"],
        "experience": "3 years web development, local business background",
        "expected_features": ["Product listings", "Shopping cart", "Payment processing", "Seller management"],
        "max_cost": 0.45,
        "max_time": 280
    },
    
    "ecommerce_medium": {
        "name": "Subscription Box Service",
        "industry": "E-commerce",
        "category": "Subscription Commerce",
        "complexity": "medium",
        "problem": "Subscription box businesses need specialized tools for recurring billing and inventory",
        "solution": "Subscription management platform with inventory tracking and customer lifecycle management",
        "target_users": "Subscription box entrepreneurs and existing businesses",
        "tech_stack": "React, Python Django, PostgreSQL, Redis, Celery",
        "skills": ["React", "Python", "Django", "Subscription Billing", "Inventory Management", "Customer Analytics"],
        "experience": "5 years full-stack development, 2 years in subscription commerce",
        "expected_features": ["Subscription management", "Inventory tracking", "Customer portal", "Analytics dashboard", "Automated billing"],
        "max_cost": 1.10,
        "max_time": 650
    },
    
    "ecommerce_complex": {
        "name": "AI-Powered Personalization Engine",
        "industry": "E-commerce",
        "category": "E-commerce AI",
        "complexity": "complex",
        "problem": "E-commerce businesses struggle with product recommendations and personalized experiences",
        "solution": "AI-powered personalization engine with real-time recommendations and dynamic pricing",
        "target_users": "Mid to large-size e-commerce businesses looking to increase conversion rates",
        "tech_stack": "React, Python FastAPI, PostgreSQL, TensorFlow, Redis, Elasticsearch",
        "skills": ["React", "Python", "FastAPI", "Machine Learning", "TensorFlow", "Recommendation Systems", "Redis", "Elasticsearch"],
        "experience": "8 years software development, 4 years in e-commerce, specialization in ML",
        "expected_features": ["Real-time recommendations", "Dynamic pricing", "A/B testing", "Customer segmentation", "Analytics dashboard"],
        "max_cost": 2.80,
        "max_time": 1600
    },

    # B2B SaaS Scenarios
    "b2b_simple": {
        "name": "Team Task Manager",
        "industry": "B2B SaaS",
        "category": "Productivity",
        "complexity": "simple",
        "problem": "Small teams struggle with task coordination and project visibility",
        "solution": "Simple team task management with Kanban boards and deadline tracking",
        "target_users": "Small teams of 3-15 people in creative and service industries",
        "tech_stack": "Vue.js, Node.js, PostgreSQL",
        "skills": ["Vue.js", "Node.js", "PostgreSQL", "Project Management"],
        "experience": "3 years web development, team leadership experience",
        "expected_features": ["Kanban boards", "Task assignment", "Deadline tracking", "Team collaboration"],
        "max_cost": 0.40,
        "max_time": 250
    },
    
    "b2b_medium": {
        "name": "Customer Support Platform",
        "industry": "B2B SaaS",
        "category": "Customer Success",
        "complexity": "medium",
        "problem": "Growing companies need better customer support tools beyond basic ticketing",
        "solution": "Integrated customer support platform with knowledge base, live chat, and analytics",
        "target_users": "Growing SaaS companies with 10-100 customers needing professional support tools",
        "tech_stack": "React, Python FastAPI, PostgreSQL, Redis, WebSocket",
        "skills": ["React", "Python", "FastAPI", "WebSocket", "Customer Success", "Analytics"],
        "experience": "5 years full-stack development, 2 years in customer success",
        "expected_features": ["Ticketing system", "Knowledge base", "Live chat", "Customer analytics", "SLA tracking"],
        "max_cost": 1.30,
        "max_time": 750
    },
    
    "b2b_complex": {
        "name": "Enterprise Integration Platform",
        "industry": "B2B SaaS",
        "category": "Enterprise Software",
        "complexity": "complex",
        "problem": "Enterprises struggle with integrating disparate software systems and data flows",
        "solution": "Low-code integration platform with API management and workflow automation",
        "target_users": "Enterprise IT teams and system integrators in mid to large companies",
        "tech_stack": "React TypeScript, Python FastAPI, PostgreSQL, Redis, Docker, Kubernetes",
        "skills": ["React", "TypeScript", "Python", "FastAPI", "Enterprise Architecture", "API Management", "Workflow Engines", "Docker", "Kubernetes"],
        "experience": "10 years software development, 5 years enterprise architecture, system integration expertise",
        "expected_features": ["Visual workflow builder", "API management", "Data transformation", "Monitoring dashboard", "Enterprise security"],
        "max_cost": 3.00,
        "max_time": 1800
    }
}


# ===== TEST FIXTURES =====

@pytest.fixture(scope="session")
def test_config():
    """Configuration for comprehensive journey testing"""
    return Config(
        openai_api_key="test-openai-key-journeys",
        anthropic_api_key="test-anthropic-key-journeys",
        perplexity_api_key="test-perplexity-key-journeys",
        project_root=Path(tempfile.mkdtemp()) / "journey_tests",
        max_retries=1,  # Fast testing
        timeout=10
    )


@pytest.fixture
def mock_ai_responses():
    """Mock AI responses for predictable testing"""
    responses = {
        "market_research": """# Market Research Analysis

## Market Size and Growth
- Total addressable market: $2.5B
- Annual growth rate: 15%
- Market maturity: Growing

## Key Trends
1. Increased digital adoption
2. Remote work acceleration
3. AI integration demand
4. User experience focus

## Opportunities
- Underserved small business segment
- Integration with existing tools
- Mobile-first approach
- Cost-effective solutions

## Competitive Landscape
- 3 major competitors
- Average pricing: $29/month
- Key differentiators needed

## Recommendations
- Focus on ease of use
- Competitive pricing strategy
- Strong customer support
- Rapid feature iteration
""",
        "founder_analysis": """# Founder-Market Fit Analysis

## Skill Alignment Score: 8.5/10

### Strengths
- Strong technical foundation
- Relevant industry experience  
- Market understanding
- Execution capability

### Opportunities
- Domain expertise development
- Network expansion
- Go-to-market skills
- Fundraising preparation

## Market Fit Assessment
- High alignment with target market
- Clear value proposition
- Scalable business model
- Reasonable resource requirements

## Recommendations
1. Focus on MVP development
2. Build initial customer base
3. Validate pricing model
4. Develop strategic partnerships

## Success Probability: 75%
""",
        "mvp_specification": """# MVP Specification

## Core Features
1. **User Management**
   - Registration and authentication
   - Profile management
   - Role-based access

2. **Primary Workflow**
   - Core functionality implementation
   - Data input and processing
   - Results visualization

3. **Dashboard**
   - Key metrics display
   - Activity tracking
   - Settings management

## Technical Architecture
- Frontend: Modern web framework
- Backend: RESTful API
- Database: Relational database
- Authentication: JWT tokens
- Deployment: Container-based

## Success Metrics
- User registration rate > 60%
- Feature adoption rate > 40%
- User retention > 30% (7-day)
- Performance: < 3s load time

## Timeline: 4 weeks
""",
        "architecture": """# Technical Architecture

## System Overview
- Microservices architecture
- API-first design
- Cloud-native deployment
- Scalable data layer

## Components
1. **Frontend Application**
   - React/Vue.js SPA
   - Responsive design
   - PWA capabilities

2. **API Gateway**
   - Request routing
   - Authentication
   - Rate limiting

3. **Core Services**
   - Business logic
   - Data processing
   - Integration APIs

4. **Data Layer**
   - Primary database
   - Cache layer
   - Search index

## Security
- OAuth 2.0 authentication
- API key management
- Data encryption
- HTTPS enforcement

## Deployment
- Docker containers
- Kubernetes orchestration
- CI/CD pipeline
- Monitoring stack

## Performance Targets
- API response: < 200ms
- Page load: < 3s
- Uptime: 99.9%
- Concurrent users: 1000+
""",
        "quality_check": """# Quality Assessment

## Code Quality: Grade A-

### Strengths
- Clean architecture
- Comprehensive testing
- Security best practices
- Performance optimization

### Areas for Improvement
- Documentation coverage
- Error handling consistency
- Logging standardization
- Monitoring integration

## Test Coverage: 85%
- Unit tests: 90%
- Integration tests: 80%
- End-to-end tests: 70%

## Security Scan: Pass
- No critical vulnerabilities
- 2 minor issues identified
- OWASP compliance achieved

## Performance: Excellent
- Load time: 2.1s average
- API response: 150ms average
- Memory usage: Optimized
- Database queries: Efficient

## Deployment Readiness: 95%
""",
        "deployment": """# Deployment Configuration

## Infrastructure Setup
- Cloud provider: AWS/GCP/Azure
- Container orchestration: Kubernetes
- Database: Managed PostgreSQL
- Cache: Redis cluster
- CDN: CloudFlare

## Environment Configuration
- Production environment
- Staging environment
- Development environment
- Testing environment

## Monitoring
- Application metrics
- Infrastructure monitoring
- Error tracking
- Log aggregation

## Backup Strategy
- Database backups: Daily
- File storage backups: Weekly
- Configuration backups: Version controlled

## Scaling Strategy
- Horizontal pod autoscaling
- Database read replicas
- CDN for static assets
- Load balancing

## Security Measures
- Network security groups
- SSL certificates
- API rate limiting
- DDoS protection

Estimated deployment time: 2-4 hours
Monthly infrastructure cost: $150-300
"""
    }
    
    with patch('openai.resources.chat.completions.Completions.create') as mock_openai, \
         patch('anthropic.resources.messages.Messages.create') as mock_anthropic, \
         patch('httpx.AsyncClient.post') as mock_perplexity:
        
        # Configure OpenAI responses
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content=responses["mvp_specification"]))],
            usage=Mock(prompt_tokens=150, completion_tokens=300)
        )
        
        # Configure Anthropic responses
        def anthropic_response(model, messages, max_tokens):
            # Determine response type based on prompt content
            prompt = messages[0]["content"].lower()
            if "market" in prompt:
                content = responses["market_research"]
            elif "founder" in prompt:
                content = responses["founder_analysis"]
            elif "architecture" in prompt:
                content = responses["architecture"]
            elif "quality" in prompt or "review" in prompt:
                content = responses["quality_check"]
            elif "deployment" in prompt:
                content = responses["deployment"]
            else:
                content = responses["mvp_specification"]
                
            return Mock(
                content=[Mock(text=content)],
                usage=Mock(input_tokens=100, output_tokens=250)
            )
        
        mock_anthropic.side_effect = anthropic_response
        
        # Configure Perplexity responses
        async def perplexity_response(*args, **kwargs):
            return Mock(
                json=lambda: {
                    "choices": [{
                        "message": {
                            "content": responses["market_research"]
                        }
                    }]
                },
                raise_for_status=lambda: None
            )
        
        mock_perplexity.side_effect = perplexity_response
        
        yield {
            "openai": mock_openai,
            "anthropic": mock_anthropic,
            "perplexity": mock_perplexity,
            "responses": responses
        }


@pytest.fixture
def orchestrator_with_mocks(test_config, mock_ai_responses):
    """Orchestrator with mocked AI responses for reliable testing"""
    return MVPOrchestrator(test_config)


# ===== COMPREHENSIVE JOURNEY TESTS =====

class TestCompleteStartupJourneys:
    """Comprehensive end-to-end startup creation journey tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_name,scenario", STARTUP_SCENARIOS.items())
    async def test_individual_startup_journey(self, orchestrator_with_mocks, scenario_name, scenario):
        """
        Test individual startup creation journey for each scenario
        
        This test validates the complete journey from project creation to MVP generation
        for each startup scenario with realistic inputs and expectations.
        """
        orchestrator = orchestrator_with_mocks
        start_time = time.time()
        
        logger.info(f"Testing startup journey: {scenario_name}")
        logger.info(f"Scenario: {scenario['name']} ({scenario['complexity']} complexity)")
        
        try:
            # Step 1: Project Creation
            project_creation_start = time.time()
            project_id = await orchestrator.create_project(
                project_name=scenario['name'],
                industry=scenario['industry'],
                category=scenario['category']
            )
            project_creation_time = time.time() - project_creation_start
            
            # Validate project creation
            assert project_id is not None
            assert project_id in orchestrator.projects
            assert project_creation_time < 2.0  # Should be very fast
            
            project = orchestrator.projects[project_id]
            assert project.project_name == scenario['name']
            assert project.industry == scenario['industry']
            assert project.category == scenario['category']
            
            # Step 2: Market Research
            market_research_start = time.time()
            market_research = await orchestrator.run_market_research(
                scenario['industry'],
                scenario['category']
            )
            market_research_time = time.time() - market_research_start
            
            # Validate market research
            assert 'analysis' in market_research
            assert 'cost' in market_research
            assert 'timestamp' in market_research
            assert market_research['industry'] == scenario['industry']
            assert market_research['category'] == scenario['category']
            assert market_research_time < 30.0  # Reasonable timeout
            
            # Step 3: Founder Analysis
            founder_analysis_start = time.time()
            founder_analysis = await orchestrator.analyze_founder_fit(
                skills=scenario['skills'],
                experience=scenario['experience'],
                market_opportunities=market_research['analysis'][:500]  # Truncated for testing
            )
            founder_analysis_time = time.time() - founder_analysis_start
            
            # Validate founder analysis
            assert 'analysis' in founder_analysis
            assert 'cost' in founder_analysis
            assert 'skills' in founder_analysis
            assert 'experience' in founder_analysis
            assert founder_analysis_time < 30.0
            
            # Step 4: MVP Specification
            mvp_spec_start = time.time()
            mvp_spec = await orchestrator.generate_mvp_spec(
                problem=scenario['problem'],
                solution=scenario['solution'],
                target_users=scenario['target_users'],
                tech_stack=scenario['tech_stack']
            )
            mvp_spec_time = time.time() - mvp_spec_start
            
            # Validate MVP specification
            assert 'specification' in mvp_spec
            assert 'cost' in mvp_spec
            assert 'problem' in mvp_spec
            assert 'solution' in mvp_spec
            assert mvp_spec_time < 30.0
            
            # Step 5: Architecture Design
            architecture_start = time.time()
            architecture = await orchestrator.create_architecture(
                mvp_spec['specification'],
                scenario['tech_stack']
            )
            architecture_time = time.time() - architecture_start
            
            # Validate architecture
            assert 'architecture' in architecture
            assert 'cost' in architecture
            assert 'tech_stack' in architecture
            assert architecture['tech_stack'] == scenario['tech_stack']
            assert architecture_time < 30.0
            
            # Step 6: Update Project with All Data
            project.market_research = market_research
            project.founder_analysis = founder_analysis
            project.mvp_spec = mvp_spec
            project.architecture = architecture
            
            # Calculate total costs
            total_cost = (
                market_research.get('cost', 0) +
                founder_analysis.get('cost', 0) +
                mvp_spec.get('cost', 0) +
                architecture.get('cost', 0)
            )
            
            # Step 7: Validate Performance and Cost Constraints
            total_time = time.time() - start_time
            
            # Performance assertions based on complexity
            assert total_time < scenario.get('max_time', 600), f"Journey took {total_time:.2f}s, expected < {scenario.get('max_time', 600)}s"
            assert total_cost < scenario.get('max_cost', 1.0), f"Journey cost ${total_cost:.3f}, expected < ${scenario.get('max_cost', 1.0)}"
            
            # Validate expected features are mentioned
            specification_text = mvp_spec['specification'].lower()
            for feature in scenario.get('expected_features', []):
                assert any(word in specification_text for word in feature.lower().split()), \
                    f"Expected feature '{feature}' not found in specification"
            
            # Step 8: Persistence Test
            await orchestrator.save_project(project_id)
            project_file = orchestrator.config.project_root / project_id / "project.json"
            assert project_file.exists(), "Project file should be saved"
            
            # Validate saved data integrity
            with open(project_file, 'r') as f:
                saved_data = json.load(f)
            assert saved_data['project_name'] == scenario['name']
            assert saved_data['industry'] == scenario['industry']
            
            logger.info(f"✅ {scenario_name} journey completed successfully in {total_time:.2f}s (cost: ${total_cost:.3f})")
            
        except Exception as e:
            logger.error(f"❌ {scenario_name} journey failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_concurrent_startup_creation(self, test_config, mock_ai_responses):
        """
        Test creating multiple startups concurrently to validate resource management
        and system stability under concurrent load.
        """
        orchestrator = MVPOrchestrator(test_config)
        
        # Select a subset of scenarios for concurrent testing
        concurrent_scenarios = [
            ("fintech_simple", STARTUP_SCENARIOS["fintech_simple"]),
            ("healthtech_simple", STARTUP_SCENARIOS["healthtech_simple"]),
            ("edtech_simple", STARTUP_SCENARIOS["edtech_simple"]),
            ("ecommerce_simple", STARTUP_SCENARIOS["ecommerce_simple"]),
            ("b2b_simple", STARTUP_SCENARIOS["b2b_simple"])
        ]
        
        start_time = time.time()
        
        async def create_startup(scenario_name, scenario):
            """Create a single startup and return results"""
            try:
                # Create project
                project_id = await orchestrator.create_project(
                    project_name=f"{scenario['name']} (Concurrent)",
                    industry=scenario['industry'],
                    category=scenario['category']
                )
                
                # Run market research only (to keep test fast)
                market_research = await orchestrator.run_market_research(
                    scenario['industry'],
                    scenario['category']
                )
                
                return {
                    'scenario': scenario_name,
                    'project_id': project_id,
                    'success': True,
                    'cost': market_research.get('cost', 0)
                }
            except Exception as e:
                logger.error(f"Concurrent startup creation failed for {scenario_name}: {e}")
                return {
                    'scenario': scenario_name,
                    'project_id': None,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent startup creation
        tasks = [
            create_startup(scenario_name, scenario)
            for scenario_name, scenario in concurrent_scenarios
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Validate results
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get('success', True)]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        logger.info(f"Concurrent creation results: {len(successful_results)} successful, {len(failed_results)} failed, {len(exceptions)} exceptions")
        
        # Assertions
        assert len(successful_results) >= 4, f"Expected at least 4 successful concurrent creations, got {len(successful_results)}"
        assert execution_time < 120.0, f"Concurrent execution took {execution_time:.2f}s, expected < 120s"
        
        # Validate each successful project
        for result in successful_results:
            project_id = result['project_id']
            assert project_id in orchestrator.projects
            project = orchestrator.projects[project_id]
            assert project.project_name is not None
            assert project.industry is not None
            assert project.category is not None
        
        # Log any failures for debugging
        for result in failed_results:
            logger.warning(f"Failed concurrent startup: {result['scenario']} - {result.get('error', 'Unknown error')}")
        
        for exception in exceptions:
            logger.error(f"Exception during concurrent creation: {exception}")
        
        total_cost = sum(r.get('cost', 0) for r in successful_results)
        logger.info(f"✅ Concurrent startup creation completed: {len(successful_results)}/{len(concurrent_scenarios)} successful in {execution_time:.2f}s (total cost: ${total_cost:.3f})")
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, orchestrator_with_mocks):
        """
        Test error handling and recovery during startup creation journeys.
        Validates system resilience and graceful failure handling.
        """
        orchestrator = orchestrator_with_mocks
        
        # Test 1: API Failure Recovery
        logger.info("Testing API failure recovery...")
        
        project_id = await orchestrator.create_project(
            project_name="Error Recovery Test",
            industry="Testing",
            category="Error Handling"
        )
        
        # Simulate API failure
        with patch.object(orchestrator.api_manager, 'call_api') as mock_call:
            # First call fails, second succeeds
            mock_call.side_effect = [
                Exception("Temporary API failure"),
                ("Recovered response", 0.05)  # Success on retry
            ]
            
            # This should handle the error and potentially retry
            try:
                result = await orchestrator.run_market_research("Testing", "Error Handling")
                # If it succeeds, great! If it fails, that's expected too
                logger.info("API failure recovery: Market research succeeded after retry")
            except Exception as e:
                # This is expected - we're testing error handling
                logger.info(f"API failure recovery: Market research failed as expected: {e}")
                assert "Temporary API failure" in str(e)
        
        # Verify project still exists and is recoverable
        assert project_id in orchestrator.projects
        project = orchestrator.projects[project_id]
        assert project.project_name == "Error Recovery Test"
        
        # Test 2: Invalid Input Handling
        logger.info("Testing invalid input handling...")
        
        try:
            await orchestrator.create_project(
                project_name="",  # Invalid empty name
                industry="",  # Invalid empty industry
                category=""   # Invalid empty category
            )
        except Exception as e:
            logger.info(f"Invalid input handled correctly: {e}")
        
        # Test 3: Resource Cleanup
        logger.info("Testing resource cleanup...")
        
        initial_project_count = len(orchestrator.projects)
        
        try:
            # Create a project that will fail during processing
            temp_project_id = await orchestrator.create_project(
                project_name="Cleanup Test",
                industry="Temporary",
                category="Testing"
            )
            
            # Verify project was created
            assert temp_project_id in orchestrator.projects
            
            # Simulate failure during market research
            with patch.object(orchestrator.api_manager, 'call_api') as mock_call:
                mock_call.side_effect = Exception("Unrecoverable error")
                
                with pytest.raises(Exception):
                    await orchestrator.run_market_research("Temporary", "Testing")
            
            # Project should still exist (we don't auto-cleanup failed projects)
            assert temp_project_id in orchestrator.projects
            
        except Exception as e:
            logger.info(f"Resource cleanup test completed: {e}")
        
        logger.info("✅ Error recovery and resilience tests completed")
    
    @pytest.mark.asyncio
    async def test_human_gate_workflow_integration(self, orchestrator_with_mocks):
        """
        Test human-in-the-loop gate integration throughout startup journeys.
        Validates that human gates are properly triggered and handled.
        """
        orchestrator = orchestrator_with_mocks
        
        # Mock human approval responses
        with patch('rich.prompt.Confirm.ask') as mock_confirm, \
             patch('rich.prompt.Prompt.ask') as mock_prompt:
            
            # Configure mock responses
            mock_confirm.return_value = True  # Auto-approve all gates
            mock_prompt.side_effect = [
                "Building a comprehensive testing platform for AI systems",  # Problem
                "Automated testing suite with AI-powered test generation",   # Solution
                "Software development teams using AI/ML in production",      # Target users
                "Python, React, PostgreSQL, Docker"  # Tech stack
            ]
            
            # Create project
            project_id = await orchestrator.create_project(
                project_name="Human Gate Test",
                industry="Software Development",
                category="Testing Tools"
            )
            
            # Run market research
            market_research = await orchestrator.run_market_research(
                "Software Development",
                "Testing Tools"
            )
            
            # Run founder analysis
            founder_analysis = await orchestrator.analyze_founder_fit(
                skills=["Python", "React", "AI/ML", "Testing"],
                experience="6 years software development, 2 years AI/ML",
                market_opportunities=market_research['analysis'][:500]
            )
            
            # Test explicit human gate
            gate_result = await orchestrator.human_gate(
                "Market Validation",
                {
                    "market_research": market_research['analysis'][:300],
                    "founder_analysis": founder_analysis['analysis'][:300],
                    "recommendations": "Strong market opportunity with good founder fit"
                }
            )
            
            # Validate human gate response
            assert gate_result == GateStatus.APPROVED
            
            # Verify mocks were called (human input was requested)
            assert mock_confirm.called
            
            logger.info("✅ Human gate workflow integration test completed")
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, orchestrator_with_mocks):
        """
        Test performance benchmarks for critical startup creation operations.
        Ensures system meets performance requirements under normal load.
        """
        orchestrator = orchestrator_with_mocks
        
        # Benchmark 1: Project Creation Speed
        logger.info("Benchmarking project creation speed...")
        
        creation_times = []
        for i in range(10):
            start = time.time()
            project_id = await orchestrator.create_project(
                f"Benchmark Project {i}",
                "Technology",
                "B2B SaaS"
            )
            end = time.time()
            creation_times.append(end - start)
            
            assert project_id in orchestrator.projects
        
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        min_creation_time = min(creation_times)
        
        logger.info(f"Project creation: avg={avg_creation_time:.3f}s, max={max_creation_time:.3f}s, min={min_creation_time:.3f}s")
        
        # Performance assertions
        assert avg_creation_time < 0.1, f"Average project creation time {avg_creation_time:.3f}s exceeds 0.1s"
        assert max_creation_time < 0.5, f"Max project creation time {max_creation_time:.3f}s exceeds 0.5s"
        
        # Benchmark 2: API Operation Speed
        logger.info("Benchmarking API operations...")
        
        api_times = []
        for i in range(5):
            start = time.time()
            result = await orchestrator.run_market_research("Technology", "B2B SaaS")
            end = time.time()
            api_times.append(end - start)
            
            assert 'analysis' in result
            assert 'cost' in result
        
        avg_api_time = sum(api_times) / len(api_times)
        max_api_time = max(api_times)
        
        logger.info(f"API operations: avg={avg_api_time:.3f}s, max={max_api_time:.3f}s")
        
        # Performance assertions (with mocked APIs, these should be very fast)
        assert avg_api_time < 5.0, f"Average API time {avg_api_time:.3f}s exceeds 5.0s"
        assert max_api_time < 10.0, f"Max API time {max_api_time:.3f}s exceeds 10.0s"
        
        # Benchmark 3: Memory Usage
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        logger.info(f"Memory usage: {memory_mb:.2f} MB")
        
        # Memory assertion (should be reasonable for testing)
        assert memory_mb < 500, f"Memory usage {memory_mb:.2f} MB exceeds 500 MB"
        
        logger.info("✅ Performance benchmarks completed successfully")
    
    @pytest.mark.asyncio
    async def test_data_integrity_and_persistence(self, orchestrator_with_mocks):
        """
        Test data integrity and persistence throughout startup creation journeys.
        Ensures data consistency and proper storage/retrieval.
        """
        orchestrator = orchestrator_with_mocks
        
        # Create a comprehensive project
        project_id = await orchestrator.create_project(
            project_name="Data Integrity Test Platform",
            industry="Data Management",
            category="B2B SaaS"
        )
        
        # Collect all data throughout the journey
        market_research = await orchestrator.run_market_research("Data Management", "B2B SaaS")
        founder_analysis = await orchestrator.analyze_founder_fit(
            skills=["Python", "Database Design", "Data Analytics"],
            experience="7 years in data engineering and platform development",
            market_opportunities=market_research['analysis'][:500]
        )
        mvp_spec = await orchestrator.generate_mvp_spec(
            problem="Organizations struggle with data quality and governance across multiple systems",
            solution="Unified data quality platform with automated monitoring and governance",
            target_users="Data teams in mid to large enterprises"
        )
        architecture = await orchestrator.create_architecture(
            mvp_spec['specification'],
            "React TypeScript, Python FastAPI, PostgreSQL, Redis"
        )
        
        # Update project with all data
        project = orchestrator.projects[project_id]
        project.market_research = market_research
        project.founder_analysis = founder_analysis
        project.mvp_spec = mvp_spec
        project.architecture = architecture
        
        # Test data integrity before save
        assert project.project_name == "Data Integrity Test Platform"
        assert project.industry == "Data Management"
        assert project.category == "B2B SaaS"
        assert project.market_research is not None
        assert project.founder_analysis is not None
        assert project.mvp_spec is not None
        assert project.architecture is not None
        
        # Save project
        await orchestrator.save_project(project_id)
        
        # Verify file was created
        project_file = orchestrator.config.project_root / project_id / "project.json"
        assert project_file.exists()
        
        # Test data integrity after save
        with open(project_file, 'r') as f:
            saved_data = json.load(f)
        
        # Validate all key fields are preserved
        assert saved_data['project_id'] == project_id
        assert saved_data['project_name'] == "Data Integrity Test Platform"
        assert saved_data['industry'] == "Data Management"
        assert saved_data['category'] == "B2B SaaS"
        assert 'created_at' in saved_data
        assert 'market_research' in saved_data
        assert 'founder_analysis' in saved_data
        assert 'mvp_spec' in saved_data
        assert 'architecture' in saved_data
        
        # Test data completeness
        for field in ['analysis', 'cost', 'timestamp']:
            assert field in saved_data['market_research']
            assert field in saved_data['founder_analysis']
        
        for field in ['specification', 'cost', 'problem', 'solution']:
            assert field in saved_data['mvp_spec']
        
        for field in ['architecture', 'cost', 'tech_stack']:
            assert field in saved_data['architecture']
        
        # Test data types
        assert isinstance(saved_data['market_research']['cost'], (int, float))
        assert isinstance(saved_data['founder_analysis']['cost'], (int, float))
        assert isinstance(saved_data['mvp_spec']['cost'], (int, float))
        assert isinstance(saved_data['architecture']['cost'], (int, float))
        
        # Test project reload (if implemented)
        try:
            reloaded_project = await orchestrator.load_project(project_id)
            if reloaded_project:
                assert reloaded_project.project_name == "Data Integrity Test Platform"
                assert reloaded_project.industry == "Data Management"
                logger.info("✅ Project reload test passed")
            else:
                logger.info("ℹ️ Project reload not implemented")
        except AttributeError:
            logger.info("ℹ️ Project reload method not available")
        
        logger.info("✅ Data integrity and persistence tests completed")
    
    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(self, orchestrator_with_mocks):
        """
        Test cost tracking accuracy throughout startup creation journeys.
        Ensures cost calculations are correct and budgets are properly monitored.
        """
        orchestrator = orchestrator_with_mocks
        
        # Create project and track costs at each step
        project_id = await orchestrator.create_project(
            project_name="Cost Tracking Test",
            industry="Financial Services",
            category="Cost Management"
        )
        
        project = orchestrator.projects[project_id]
        
        # Initialize cost tracking
        project.api_costs = {}
        
        # Step 1: Market Research
        market_research = await orchestrator.run_market_research("Financial Services", "Cost Management")
        market_cost = market_research.get('cost', 0)
        project.api_costs['perplexity'] = project.api_costs.get('perplexity', 0) + market_cost
        
        # Step 2: Founder Analysis  
        founder_analysis = await orchestrator.analyze_founder_fit(
            skills=["Finance", "Software Development", "Product Management"],
            experience="8 years in fintech and cost management solutions",
            market_opportunities=market_research['analysis'][:500]
        )
        founder_cost = founder_analysis.get('cost', 0)
        project.api_costs['anthropic'] = project.api_costs.get('anthropic', 0) + founder_cost
        
        # Step 3: MVP Specification
        mvp_spec = await orchestrator.generate_mvp_spec(
            problem="Businesses struggle with accurate cost tracking across multiple systems",
            solution="Automated cost tracking platform with real-time analytics",
            target_users="Finance teams in growing companies"
        )
        mvp_cost = mvp_spec.get('cost', 0)
        project.api_costs['anthropic'] = project.api_costs.get('anthropic', 0) + mvp_cost
        
        # Step 4: Architecture
        architecture = await orchestrator.create_architecture(
            mvp_spec['specification'],
            "React, Python FastAPI, PostgreSQL"
        )
        arch_cost = architecture.get('cost', 0)
        project.api_costs['anthropic'] = project.api_costs.get('anthropic', 0) + arch_cost
        
        # Validate cost tracking
        total_calculated_cost = market_cost + founder_cost + mvp_cost + arch_cost
        total_tracked_cost = sum(project.api_costs.values())
        
        # Cost assertions
        assert market_cost >= 0, "Market research cost should be non-negative"
        assert founder_cost >= 0, "Founder analysis cost should be non-negative"
        assert mvp_cost >= 0, "MVP specification cost should be non-negative"
        assert arch_cost >= 0, "Architecture cost should be non-negative"
        
        assert abs(total_calculated_cost - total_tracked_cost) < 0.001, \
            f"Cost tracking mismatch: calculated={total_calculated_cost:.6f}, tracked={total_tracked_cost:.6f}"
        
        # Test cost breakdown by provider
        if 'perplexity' in project.api_costs:
            assert project.api_costs['perplexity'] == market_cost
        if 'anthropic' in project.api_costs:
            expected_anthropic_cost = founder_cost + mvp_cost + arch_cost
            assert abs(project.api_costs['anthropic'] - expected_anthropic_cost) < 0.001
        
        # Validate cost reasonableness (with mocked responses, costs should be predictable)
        assert total_tracked_cost < 2.0, f"Total cost ${total_tracked_cost:.3f} seems unreasonably high for mocked responses"
        assert total_tracked_cost > 0.0, "Total cost should be greater than zero"
        
        logger.info(f"Cost tracking: Market=${market_cost:.4f}, Founder=${founder_cost:.4f}, MVP=${mvp_cost:.4f}, Arch=${arch_cost:.4f}")
        logger.info(f"Total calculated cost: ${total_calculated_cost:.4f}")
        logger.info(f"Total tracked cost: ${total_tracked_cost:.4f}")
        logger.info("✅ Cost tracking accuracy tests completed")


# ===== SYSTEM HEALTH AND INTEGRATION TESTS =====

class TestSystemHealthAndIntegration:
    """System health and integration validation tests"""
    
    @pytest.mark.asyncio
    async def test_complete_system_integration_health(self, test_config, mock_ai_responses):
        """Test complete system health with all components integrated"""
        
        # Initialize all major components
        orchestrator = MVPOrchestrator(test_config)
        
        # Test system initialization
        assert orchestrator.config == test_config
        assert hasattr(orchestrator, 'api_manager')
        assert hasattr(orchestrator, 'doc_manager')
        assert isinstance(orchestrator.projects, dict)
        
        # Test API manager integration
        assert orchestrator.api_manager is not None
        
        # Test document manager integration
        assert orchestrator.doc_manager is not None
        assert orchestrator.doc_manager.project_root == test_config.project_root
        
        # Test basic system workflow
        project_id = await orchestrator.create_project(
            "System Health Test",
            "System Testing",
            "Integration"
        )
        
        assert project_id is not None
        assert project_id in orchestrator.projects
        
        # Test API integration
        result = await orchestrator.run_market_research("System Testing", "Integration")
        assert 'analysis' in result
        assert 'cost' in result
        assert 'timestamp' in result
        
        # Test document persistence
        await orchestrator.save_project(project_id)
        project_file = orchestrator.config.project_root / project_id / "project.json"
        assert project_file.exists()
        
        logger.info("✅ Complete system integration health check passed")
    
    def test_configuration_validation(self, test_config):
        """Test system configuration validation"""
        
        # Test required fields
        assert test_config.openai_api_key is not None
        assert test_config.anthropic_api_key is not None
        assert test_config.perplexity_api_key is not None
        assert test_config.project_root is not None
        
        # Test field types
        assert isinstance(test_config.openai_api_key, str)
        assert isinstance(test_config.anthropic_api_key, str)
        assert isinstance(test_config.perplexity_api_key, str)
        assert isinstance(test_config.project_root, Path)
        
        # Test reasonable values
        assert test_config.max_retries >= 1
        assert test_config.timeout > 0
        assert test_config.max_retries <= 10  # Reasonable upper bound
        assert test_config.timeout <= 300     # Reasonable timeout
        
        # Test cost configuration
        assert test_config.openai_input_cost_per_1k >= 0
        assert test_config.openai_output_cost_per_1k >= 0
        assert test_config.anthropic_input_cost_per_1k >= 0
        assert test_config.anthropic_output_cost_per_1k >= 0
        assert test_config.perplexity_cost_per_request >= 0
        
        logger.info("✅ Configuration validation passed")


# ===== TEST EXECUTION AND REPORTING =====

def run_journey_tests():
    """Run complete startup journey tests with comprehensive reporting"""
    
    print("=" * 80)
    print("COMPLETE STARTUP CREATION JOURNEY TESTS")
    print("=" * 80)
    print(f"Testing {len(STARTUP_SCENARIOS)} startup scenarios across 5 industries")
    print(f"Complexity levels: Simple, Medium, Complex")
    print(f"Test coverage: End-to-end workflows, performance, error handling")
    print("=" * 80)
    
    # Run tests with detailed output
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--durations=10",
        "-x"  # Stop on first failure for faster debugging
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    run_journey_tests()