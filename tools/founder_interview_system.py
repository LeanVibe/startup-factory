#!/usr/bin/env python3
"""
Founder Interview System - AI Architect Agent
Transforms founder conversations into actionable business blueprints.

This is the core intelligence system that replaces technical configuration
with conversational founder interviews, understanding business problems
and generating comprehensive product specifications.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

try:
    import anthropic
    from pydantic import BaseModel, Field
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install anthropic pydantic rich")
    exit(1)

console = Console()
logger = logging.getLogger(__name__)


class BusinessModel(str, Enum):
    """Core business model types"""
    B2B_SAAS = "b2b_saas"
    B2C_SAAS = "b2c_saas"
    MARKETPLACE = "marketplace"
    ECOMMERCE = "ecommerce"
    CONTENT_PLATFORM = "content_platform"
    SERVICE_BUSINESS = "service_business"
    UNKNOWN = "unknown"


class IndustryVertical(str, Enum):
    """Industry verticals for specialized features"""
    HEALTHCARE = "healthcare"
    FINTECH = "fintech"
    EDUCATION = "education"
    REAL_ESTATE = "real_estate"
    LOGISTICS = "logistics"
    MEDIA = "media"
    GENERAL = "general"


@dataclass
class FounderProfile:
    """Founder's background and constraints"""
    name: str
    technical_background: bool = False
    previous_startups: int = 0
    target_timeline: str = "3_months"  # "1_month", "3_months", "6_months"
    budget_constraints: str = "bootstrap"  # "bootstrap", "seed_funded", "well_funded"
    team_size: int = 1
    primary_skills: List[str] = field(default_factory=list)
    biggest_fear: Optional[str] = None


@dataclass
class ProblemStatement:
    """Core problem the startup aims to solve"""
    problem_description: str
    target_audience: str
    current_solutions: List[str] = field(default_factory=list)
    solution_gaps: List[str] = field(default_factory=list)
    pain_severity: int = 1  # 1-10 scale
    market_size_estimate: Optional[str] = None
    validation_evidence: List[str] = field(default_factory=list)


@dataclass
class SolutionConcept:
    """Proposed solution approach"""
    core_value_proposition: str
    key_features: List[str] = field(default_factory=list)
    user_journey: List[str] = field(default_factory=list)
    differentiation_factors: List[str] = field(default_factory=list)
    success_metrics: List[str] = field(default_factory=list)
    monetization_strategy: str = "subscription"
    pricing_model: Optional[str] = None


@dataclass
class BusinessBlueprint:
    """Complete business specification generated from founder interview"""
    founder_profile: FounderProfile
    problem_statement: ProblemStatement
    solution_concept: SolutionConcept
    business_model: BusinessModel
    industry_vertical: IndustryVertical
    
    # Generated technical specifications
    data_entities: List[Dict[str, Any]] = field(default_factory=list)
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    user_stories: List[str] = field(default_factory=list)
    wireframes: Dict[str, Any] = field(default_factory=dict)
    tech_stack_recommendations: Dict[str, Any] = field(default_factory=dict)
    
    # Project metadata
    project_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0


class FounderInterviewAgent:
    """AI Agent specialized in conducting founder interviews and extracting business intelligence"""
    
    def __init__(self, anthropic_client: Optional[anthropic.Anthropic] = None):
        self.client = anthropic_client or self._initialize_client()
        self.conversation_history: List[Dict[str, str]] = []
    
    def _initialize_client(self) -> Optional[anthropic.Anthropic]:
        """Initialize Anthropic client with graceful fallback"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return anthropic.Anthropic(api_key=api_key)
        
        # Graceful fallback with intelligent business analysis
        console.print("[yellow]⚠️  No API key found. Using intelligent business analysis fallbacks.[/yellow]")
        console.print("For full AI conversation features, set ANTHROPIC_API_KEY environment variable.")
        return None
        
    async def conduct_interview(self) -> BusinessBlueprint:
        """Main interview flow that guides founders through business definition"""
        console.print(Panel(
            "[bold blue]🚀 Welcome to the Startup Factory![/bold blue]\n\n"
            "I'm your AI Architect. I'll help you transform your business idea\n"
            "into a complete MVP specification through a guided conversation.\n\n"
            "This process takes about 15-20 minutes and will result in:\n"
            "• A complete business blueprint\n"
            "• Technical architecture recommendations\n"
            "• User stories and wireframes\n"
            "• A live MVP ready for deployment",
            title="AI Architect Agent"
        ))
        
        # Stage 1: Founder Profile
        console.print("\n[bold cyan]Stage 1: Understanding You[/bold cyan]")
        founder_profile = await self._collect_founder_profile()
        
        # Stage 2: Problem Discovery
        console.print("\n[bold cyan]Stage 2: Problem Discovery[/bold cyan]")
        problem_statement = await self._discover_problem(founder_profile)
        
        # Stage 3: Solution Design
        console.print("\n[bold cyan]Stage 3: Solution Design[/bold cyan]")
        solution_concept = await self._design_solution(founder_profile, problem_statement)
        
        # Stage 4: Business Model Classification
        console.print("\n[bold cyan]Stage 4: Business Model Analysis[/bold cyan]")
        business_model, industry_vertical = await self._classify_business(
            problem_statement, solution_concept
        )
        
        # Stage 5: Technical Specification Generation
        console.print("\n[bold cyan]Stage 5: Technical Architecture[/bold cyan]")
        blueprint = BusinessBlueprint(
            founder_profile=founder_profile,
            problem_statement=problem_statement,
            solution_concept=solution_concept,
            business_model=business_model,
            industry_vertical=industry_vertical,
            project_id=self._generate_project_id()
        )
        
        await self._generate_technical_specs(blueprint)
        
        # Final validation
        console.print("\n[bold green]Blueprint Generated![/bold green]")
        self._display_blueprint_summary(blueprint)
        
        if Confirm.ask("\nDoes this blueprint accurately capture your vision?"):
            blueprint.confidence_score = 0.95
            console.print("[green]✅ Blueprint approved! Moving to generation...[/green]")
        else:
            blueprint.confidence_score = 0.70
            console.print("[yellow]⚠️  Blueprint needs refinement, but proceeding...[/yellow]")
        
        return blueprint
    
    async def _collect_founder_profile(self) -> FounderProfile:
        """Collect founder background and constraints"""
        console.print("Let's start by understanding your background and goals.")
        
        name = Prompt.ask("What's your name?")
        
        # Technical background assessment
        has_tech_background = Confirm.ask(
            "Do you have a technical background (programming, engineering, etc.)?"
        )
        
        # Previous startup experience
        previous_startups = 0
        if Confirm.ask("Have you founded a startup before?"):
            previous_startups = int(Prompt.ask(
                "How many startups have you founded previously?",
                default="1"
            ))
        
        # Timeline and constraints
        timeline = Prompt.ask(
            "What's your target timeline to launch?",
            choices=["1_month", "3_months", "6_months"],
            default="3_months"
        )
        
        budget = Prompt.ask(
            "What's your funding situation?",
            choices=["bootstrap", "seed_funded", "well_funded"],
            default="bootstrap"
        )
        
        team_size = int(Prompt.ask("How many people are on your team?", default="1"))
        
        # Skills assessment
        skills_input = Prompt.ask(
            "What are your primary skills? (comma-separated)",
            default="business, marketing"
        )
        skills = [skill.strip() for skill in skills_input.split(",")]
        
        # Biggest concern
        biggest_fear = Prompt.ask(
            "What's your biggest fear about building this startup?",
            default=""
        )
        
        return FounderProfile(
            name=name,
            technical_background=has_tech_background,
            previous_startups=previous_startups,
            target_timeline=timeline,
            budget_constraints=budget,
            team_size=team_size,
            primary_skills=skills,
            biggest_fear=biggest_fear if biggest_fear else None
        )
    
    async def _discover_problem(self, founder: FounderProfile) -> ProblemStatement:
        """Deep dive into problem discovery using AI-guided questions"""
        console.print(f"\nHi {founder.name}! Now let's explore the problem you're solving.")
        
        # Core problem identification
        problem_desc = Prompt.ask(
            "In 2-3 sentences, describe the main problem your startup will solve:"
        )
        
        # Target audience
        target_audience = Prompt.ask(
            "Who specifically experiences this problem? (be as specific as possible)"
        )
        
        # Use AI to generate follow-up questions based on the problem
        follow_up_questions = await self._generate_problem_followups(problem_desc, target_audience)
        
        current_solutions = []
        solution_gaps = []
        validation_evidence = []
        
        # AI-guided follow-up questions
        for question in follow_up_questions:
            response = Prompt.ask(f"\n{question}")
            
            if "current" in question.lower() or "existing" in question.lower():
                current_solutions.append(response)
            elif "gap" in question.lower() or "missing" in question.lower():
                solution_gaps.append(response)
            elif "evidence" in question.lower() or "validation" in question.lower():
                validation_evidence.append(response)
        
        # Pain severity assessment
        pain_severity = int(Prompt.ask(
            "On a scale of 1-10, how painful is this problem for your target audience?",
            choices=[str(i) for i in range(1, 11)],
            default="7"
        ))
        
        # Market size estimation
        market_size = Prompt.ask(
            "What's your rough estimate of the market size? (e.g., '$1B market', '10M potential users')",
            default=""
        )
        
        return ProblemStatement(
            problem_description=problem_desc,
            target_audience=target_audience,
            current_solutions=current_solutions,
            solution_gaps=solution_gaps,
            pain_severity=pain_severity,
            market_size_estimate=market_size if market_size else None,
            validation_evidence=validation_evidence
        )
    
    async def _generate_problem_followups(self, problem_desc: str, target_audience: str) -> List[str]:
        """Use AI to generate intelligent follow-up questions about the problem"""
        # Prefer provider manager; fallback to direct client or rule-based
        try:
            from tools.ai_providers import create_default_provider_manager
            from tools.core_types import Task, TaskType, generate_task_id
            provider_manager = create_default_provider_manager()
            task = Task(
                id=generate_task_id(),
                startup_id="interview",
                type=TaskType.FOUNDER_ANALYSIS,
                description="Generate intelligent follow-up questions",
                prompt=(
                    f"Founder problem: {problem_desc}\n"
                    f"Target audience: {target_audience}\n\n"
                    "Generate 3-4 intelligent follow-up questions that cover existing solutions, validation, compliance, and concrete scenarios. One per line."
                ),
                max_tokens=300,
            )
            result = await provider_manager.process_task(task)
            if result.success and result.content:
                qs = [q.strip() for q in result.content.strip().split('\n') if q.strip()]
                return qs[:4]
        except Exception:
            pass

        if not self.client:
            # Enhanced intelligent fallback based on business intelligence
            return await self._intelligent_problem_followups(problem_desc, target_audience)
        
        prompt = f"""
        A founder is describing their startup problem:
        Problem: {problem_desc}
        Target Audience: {target_audience}
        
        Generate 3-4 intelligent follow-up questions that will help understand:
        1. Existing solutions and their limitations
        2. Evidence of problem validation
        3. Industry-specific challenges and compliance requirements
        4. Specific use cases or scenarios
        
        Return only the questions, one per line, without numbering.
        Keep questions conversational and founder-friendly.
        Focus on business intelligence extraction, not just generic validation.
        """
        
        try:
            response = await asyncio.create_task(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            
            questions = [q.strip() for q in response.content[0].text.strip().split('\n') if q.strip()]
            return questions[:4]  # Limit to 4 questions
            
        except Exception as e:
            logger.warning(f"AI follow-up generation failed: {e}")
            return await self._intelligent_problem_followups(problem_desc, target_audience)
    
    async def _intelligent_problem_followups(self, problem_desc: str, target_audience: str) -> List[str]:
        """Intelligent fallback for problem follow-up questions with business context awareness"""
        
        problem_lower = problem_desc.lower()
        audience_lower = target_audience.lower()
        
        # Industry-specific questions
        industry_questions = {
            "healthcare": [
                "What healthcare regulations or compliance requirements affect this problem?",
                "How do current medical workflows handle this situation?",
                "What documentation or audit trails are needed for this process?"
            ],
            "fintech": [
                "What financial regulations impact how this problem can be solved?",
                "How do users currently handle financial data security for this problem?", 
                "What compliance frameworks (PCI, SOX, etc.) need to be considered?"
            ],
            "education": [
                "What educational standards or accreditation requirements are relevant?",
                "How do current educational tools address student privacy (FERPA compliance)?",
                "What reporting or analytics do educators need for this problem?"
            ]
        }
        
        # Detect industry context
        questions = []
        
        if any(term in problem_lower or term in audience_lower for term in ['health', 'medical', 'doctor', 'patient']):
            questions.extend(industry_questions["healthcare"])
        elif any(term in problem_lower or term in audience_lower for term in ['finance', 'financial', 'payment', 'bank', 'money', 'fraud', 'transaction']):
            questions.extend(industry_questions["fintech"])
        elif any(term in problem_lower or term in audience_lower for term in ['education', 'learning', 'student', 'school', 'teacher']):
            questions.extend(industry_questions["education"])
        else:
            # Business-intelligent generic questions
            questions = [
                "What existing solutions do people use, and what's frustrating about them?", 
                "Can you walk me through a specific time this problem cost someone time or money?",
                "What would happen if this problem was never solved?",
                "Who else in the organization cares about solving this problem?"
            ]
        
        return questions[:4]
    
    async def _design_solution(self, founder: FounderProfile, problem: ProblemStatement) -> SolutionConcept:
        """Guide founder through solution design with AI assistance"""
        console.print("\nNow let's design your solution approach.")
        
        # Core value proposition
        value_prop = Prompt.ask(
            "In one sentence, what's your unique value proposition?"
        )
        
        # Key features brainstorming
        console.print("\nLet's identify the key features of your MVP.")
        features = []
        for i in range(3, 8):  # 3-7 features
            feature = Prompt.ask(f"Feature {i-2} (or press Enter if done)", default="")
            if not feature:
                break
            features.append(feature)
        
        # User journey mapping
        console.print("\nLet's map out the user journey.")
        journey_steps = []
        for i in range(1, 6):  # Up to 5 journey steps
            step = Prompt.ask(f"User journey step {i} (or press Enter if done)", default="")
            if not step:
                break
            journey_steps.append(step)
        
        # Differentiation factors
        differentiation = Prompt.ask(
            "What makes your solution different from existing alternatives?"
        ).split(',')
        differentiation = [d.strip() for d in differentiation]
        
        # Success metrics
        metrics_input = Prompt.ask(
            "How will you measure success? (comma-separated metrics)",
            default="user signups, revenue, user retention"
        )
        success_metrics = [m.strip() for m in metrics_input.split(',')]
        
        # Monetization strategy
        monetization = Prompt.ask(
            "How will you make money?",
            choices=["subscription", "one_time_purchase", "freemium", "marketplace_fees", "advertising", "other"],
            default="subscription"
        )
        
        pricing_model = None
        if monetization in ["subscription", "freemium"]:
            pricing_model = Prompt.ask("What's your expected price point?", default="")
        
        return SolutionConcept(
            core_value_proposition=value_prop,
            key_features=features,
            user_journey=journey_steps,
            differentiation_factors=differentiation,
            success_metrics=success_metrics,
            monetization_strategy=monetization,
            pricing_model=pricing_model if pricing_model else None
        )
    
    async def _classify_business(self, problem: ProblemStatement, solution: SolutionConcept) -> Tuple[BusinessModel, IndustryVertical]:
        """Use AI to classify business model and industry vertical with intelligent fallback"""
        
        # Prefer provider manager; fallback to client then rule-based
        try:
            from tools.ai_providers import create_default_provider_manager
            from tools.core_types import Task, TaskType, generate_task_id
            provider_manager = create_default_provider_manager()
            prompt = (
                f"Analyze and classify business model + industry.\n"
                f"Problem: {problem.problem_description}\n"
                f"Target Audience: {problem.target_audience}\n"
                f"Solution: {solution.core_value_proposition}\n"
                f"Key Features: {', '.join(solution.key_features)}\n"
                f"Monetization: {solution.monetization_strategy}\n\n"
                "Return 'business_model,industry_vertical' (e.g., b2b_saas,healthcare)."
            )
            task = Task(
                id=generate_task_id(),
                startup_id="interview",
                type=TaskType.MVP_SPECIFICATION,
                description="Classify business model and industry",
                prompt=prompt,
                max_tokens=50,
            )
            result = await provider_manager.process_task(task)
            if result.success and result.content and ',' in result.content:
                bm_str, ind_str = [s.strip() for s in result.content.split(',', 1)]
                return BusinessModel(bm_str), IndustryVertical(ind_str)
        except Exception:
            pass

        if not self.client:
            return await self._intelligent_business_classification(problem, solution)
        
        classification_prompt = f"""
        Analyze this startup and classify its business model and industry:
        
        Problem: {problem.problem_description}
        Target Audience: {problem.target_audience}
        Solution: {solution.core_value_proposition}
        Key Features: {', '.join(solution.key_features)}
        Monetization: {solution.monetization_strategy}
        
        Classify this startup:
        
        Business Model (choose one):
        - b2b_saas: Software for businesses, subscription model
        - b2c_saas: Software for consumers, subscription model
        - marketplace: Two-sided platform connecting buyers/sellers
        - ecommerce: Direct selling of products
        - content_platform: Publishing, media, content creation
        - service_business: Professional services, consulting
        
        Industry Vertical (choose one):
        - healthcare: Medical, health, wellness
        - fintech: Financial services, payments, investing
        - education: Learning, training, schools
        - real_estate: Property, housing, real estate
        - logistics: Shipping, delivery, supply chain
        - media: Publishing, entertainment, content
        - general: Does not fit specific vertical
        
        Respond with only: BusinessModel,IndustryVertical (e.g., "b2b_saas,healthcare")
        """
        
        try:
            response = await asyncio.create_task(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    messages=[{"role": "user", "content": classification_prompt}]
                )
            )
            
            classification = response.content[0].text.strip()
            business_model_str, industry_str = classification.split(',')
            
            business_model = BusinessModel(business_model_str.strip())
            industry_vertical = IndustryVertical(industry_str.strip())
            
            console.print(f"[green]✅ AI Classified as: {business_model.value} in {industry_vertical.value}[/green]")
            
            return business_model, industry_vertical
            
        except Exception as e:
            logger.warning(f"AI classification failed: {e}")
            return await self._intelligent_business_classification(problem, solution)
    
    async def _intelligent_business_classification(self, problem: ProblemStatement, solution: SolutionConcept) -> Tuple[BusinessModel, IndustryVertical]:
        """Intelligent rule-based business classification with context awareness"""
        
        # Combine all text for analysis
        all_text = " ".join([
            problem.problem_description,
            problem.target_audience,
            solution.core_value_proposition,
            " ".join(solution.key_features),
            solution.monetization_strategy
        ]).lower()
        
        # Industry classification
        industry_vertical = IndustryVertical.GENERAL
        
        industry_keywords = {
            IndustryVertical.HEALTHCARE: ['health', 'medical', 'doctor', 'patient', 'hospital', 'clinic', 'healthcare', 'hipaa', 'medical records'],
            IndustryVertical.FINTECH: ['finance', 'payment', 'bank', 'money', 'transaction', 'financial', 'investing', 'trading', 'lending'],
            IndustryVertical.EDUCATION: ['education', 'learning', 'student', 'school', 'teacher', 'curriculum', 'training', 'course'],
            IndustryVertical.REAL_ESTATE: ['property', 'real estate', 'housing', 'rental', 'lease', 'mortgage', 'property management'],
            IndustryVertical.LOGISTICS: ['shipping', 'delivery', 'logistics', 'supply chain', 'warehouse', 'transportation', 'fulfillment'],
            IndustryVertical.MEDIA: ['content', 'media', 'publishing', 'entertainment', 'video', 'streaming', 'social media']
        }
        
        # Find best industry match
        max_matches = 0
        for vertical, keywords in industry_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in all_text)
            if matches > max_matches:
                max_matches = matches
                industry_vertical = vertical
        
        # Business model classification
        business_model = BusinessModel.B2C_SAAS  # Default
        
        if any(term in all_text for term in ['business', 'enterprise', 'company', 'organization', 'b2b']):
            business_model = BusinessModel.B2B_SAAS
        elif any(term in all_text for term in ['marketplace', 'platform', 'connect', 'two-sided']):
            business_model = BusinessModel.MARKETPLACE
        elif any(term in all_text for term in ['ecommerce', 'shop', 'store', 'product', 'selling']):
            business_model = BusinessModel.ECOMMERCE
        elif any(term in all_text for term in ['content', 'publishing', 'media', 'blog']):
            business_model = BusinessModel.CONTENT_PLATFORM
        elif any(term in all_text for term in ['service', 'consulting', 'professional services']):
            business_model = BusinessModel.SERVICE_BUSINESS
        
        console.print(f"[cyan]🧠 Intelligent Classification: {business_model.value} in {industry_vertical.value}[/cyan]")
        
        return business_model, industry_vertical
    
    async def _generate_technical_specs(self, blueprint: BusinessBlueprint):
        """Generate technical specifications from business blueprint using AI"""
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Generating technical specifications...", total=4)
            
            # Generate data entities
            progress.update(task, description="Designing data model...")
            blueprint.data_entities = await self._generate_data_entities(blueprint)
            progress.advance(task)
            
            # Generate API endpoints
            progress.update(task, description="Designing API endpoints...")
            blueprint.api_endpoints = await self._generate_api_endpoints(blueprint)
            progress.advance(task)
            
            # Generate user stories
            progress.update(task, description="Creating user stories...")
            blueprint.user_stories = await self._generate_user_stories(blueprint)
            progress.advance(task)
            
            # Generate tech stack recommendations
            progress.update(task, description="Selecting technology stack...")
            blueprint.tech_stack_recommendations = await self._generate_tech_stack(blueprint)
            progress.advance(task)
    
    async def _generate_data_entities(self, blueprint: BusinessBlueprint) -> List[Dict[str, Any]]:
        """Generate data model entities based on business requirements"""
        
        entities_prompt = f"""
        Based on this business blueprint, design the core data entities:
        
        Business Model: {blueprint.business_model.value}
        Key Features: {', '.join(blueprint.solution_concept.key_features)}
        User Journey: {' -> '.join(blueprint.solution_concept.user_journey)}
        
        Generate 3-5 core data entities with their attributes.
        Return as JSON array with this format:
        [
          {{
            "name": "User",
            "attributes": [
              {{"name": "email", "type": "string", "required": true}},
              {{"name": "created_at", "type": "datetime", "required": true}}
            ]
          }}
        ]
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": entities_prompt}]
            )
            
            # Extract JSON from response
            content = response.content[0].text
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            json_str = content[json_start:json_end]
            
            return json.loads(json_str)
            
        except Exception as e:
            logger.warning(f"Data entity generation failed: {e}")
            # Fallback basic entities
            return [
                {
                    "name": "User",
                    "attributes": [
                        {"name": "email", "type": "string", "required": True},
                        {"name": "password_hash", "type": "string", "required": True},
                        {"name": "created_at", "type": "datetime", "required": True}
                    ]
                }
            ]
    
    async def _generate_api_endpoints(self, blueprint: BusinessBlueprint) -> List[Dict[str, Any]]:
        """Generate API endpoints based on features and user journey"""
        
        # Use features and user journey to infer needed endpoints
        endpoints = [
            {"method": "POST", "path": "/auth/login", "description": "User authentication"},
            {"method": "POST", "path": "/auth/register", "description": "User registration"},
            {"method": "GET", "path": "/user/profile", "description": "Get user profile"},
        ]
        
        # Add feature-specific endpoints based on key features
        for feature in blueprint.solution_concept.key_features:
            if any(word in feature.lower() for word in ["dashboard", "analytics"]):
                endpoints.append({
                    "method": "GET", 
                    "path": "/dashboard/stats", 
                    "description": f"Get {feature.lower()} data"
                })
            elif any(word in feature.lower() for word in ["create", "add", "upload"]):
                endpoints.append({
                    "method": "POST", 
                    "path": f"/{feature.split()[0].lower()}", 
                    "description": f"Create new {feature.lower()}"
                })
        
        return endpoints
    
    async def _generate_user_stories(self, blueprint: BusinessBlueprint) -> List[str]:
        """Generate user stories from the business blueprint"""
        
        stories = []
        
        # Authentication stories
        stories.extend([
            "As a user, I want to create an account so that I can access the platform",
            "As a user, I want to log in securely so that I can access my data"
        ])
        
        # Feature-based stories
        for feature in blueprint.solution_concept.key_features:
            stories.append(f"As a user, I want to {feature.lower()} so that I can achieve my goals")
        
        # Journey-based stories
        for step in blueprint.solution_concept.user_journey:
            stories.append(f"As a user, I want to {step.lower()} so that I can progress through my workflow")
        
        return stories[:10]  # Limit to 10 stories for MVP
    
    async def _generate_tech_stack(self, blueprint: BusinessBlueprint) -> Dict[str, Any]:
        """Generate technology stack recommendations based on business requirements"""
        
        # Base stack (NeoForge template)
        tech_stack = {
            "backend": {
                "framework": "FastAPI",
                "database": "PostgreSQL",
                "orm": "SQLAlchemy",
                "auth": "JWT tokens",
                "deployment": "Docker + DigitalOcean"
            },
            "frontend": {
                "framework": "Lit Web Components",
                "build_tool": "Vite",
                "styling": "CSS Custom Properties",
                "deployment": "Static hosting"
            },
            "infrastructure": {
                "hosting": "DigitalOcean Droplet",
                "domain": "Namecheap",
                "cdn": "Cloudflare",
                "monitoring": "Built-in dashboard"
            }
        }
        
        # Add industry-specific recommendations
        if blueprint.industry_vertical == IndustryVertical.FINTECH:
            tech_stack["security"] = ["PCI compliance", "Encryption at rest", "Audit logging"]
            tech_stack["payments"] = "Stripe integration"
        elif blueprint.industry_vertical == IndustryVertical.HEALTHCARE:
            tech_stack["security"] = ["HIPAA compliance", "Data encryption", "Access controls"]
        
        # Add business model specific features
        if blueprint.business_model == BusinessModel.MARKETPLACE:
            tech_stack["payments"] = "Multi-party payments (Stripe Connect)"
            tech_stack["features"] = ["Review system", "Rating system", "Messaging"]
        elif blueprint.business_model == BusinessModel.B2B_SAAS:
            tech_stack["features"] = ["Multi-tenant architecture", "Usage analytics", "Team management"]
        
        return tech_stack
    
    def _generate_project_id(self) -> str:
        """Generate unique project identifier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"startup_{timestamp}"
    
    def _display_blueprint_summary(self, blueprint: BusinessBlueprint):
        """Display a summary of the generated blueprint"""
        
        table = Table(title="Business Blueprint Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="white")
        
        table.add_row("Problem", blueprint.problem_statement.problem_description[:80] + "...")
        table.add_row("Solution", blueprint.solution_concept.core_value_proposition)
        table.add_row("Business Model", blueprint.business_model.value)
        table.add_row("Industry", blueprint.industry_vertical.value)
        table.add_row("Key Features", ", ".join(blueprint.solution_concept.key_features[:3]))
        table.add_row("Data Entities", str(len(blueprint.data_entities)))
        table.add_row("API Endpoints", str(len(blueprint.api_endpoints)))
        table.add_row("User Stories", str(len(blueprint.user_stories)))
        
        console.print(table)
    
    def save_blueprint(self, blueprint: BusinessBlueprint, output_dir: Path = None) -> Path:
        """Save blueprint to JSON file"""
        if output_dir is None:
            output_dir = Path("production_projects")
        
        output_dir.mkdir(exist_ok=True)
        
        # Convert to serializable format
        blueprint_data = {
            "project_id": blueprint.project_id,
            "created_at": blueprint.created_at.isoformat(),
            "confidence_score": blueprint.confidence_score,
            "founder_profile": {
                "name": blueprint.founder_profile.name,
                "technical_background": blueprint.founder_profile.technical_background,
                "previous_startups": blueprint.founder_profile.previous_startups,
                "target_timeline": blueprint.founder_profile.target_timeline,
                "budget_constraints": blueprint.founder_profile.budget_constraints,
                "team_size": blueprint.founder_profile.team_size,
                "primary_skills": blueprint.founder_profile.primary_skills,
                "biggest_fear": blueprint.founder_profile.biggest_fear
            },
            "problem_statement": {
                "problem_description": blueprint.problem_statement.problem_description,
                "target_audience": blueprint.problem_statement.target_audience,
                "current_solutions": blueprint.problem_statement.current_solutions,
                "solution_gaps": blueprint.problem_statement.solution_gaps,
                "pain_severity": blueprint.problem_statement.pain_severity,
                "market_size_estimate": blueprint.problem_statement.market_size_estimate,
                "validation_evidence": blueprint.problem_statement.validation_evidence
            },
            "solution_concept": {
                "core_value_proposition": blueprint.solution_concept.core_value_proposition,
                "key_features": blueprint.solution_concept.key_features,
                "user_journey": blueprint.solution_concept.user_journey,
                "differentiation_factors": blueprint.solution_concept.differentiation_factors,
                "success_metrics": blueprint.solution_concept.success_metrics,
                "monetization_strategy": blueprint.solution_concept.monetization_strategy,
                "pricing_model": blueprint.solution_concept.pricing_model
            },
            "business_model": blueprint.business_model.value,
            "industry_vertical": blueprint.industry_vertical.value,
            "technical_specifications": {
                "data_entities": blueprint.data_entities,
                "api_endpoints": blueprint.api_endpoints,
                "user_stories": blueprint.user_stories,
                "tech_stack_recommendations": blueprint.tech_stack_recommendations
            }
        }
        
        output_file = output_dir / f"{blueprint.project_id}_blueprint.json"
        with open(output_file, 'w') as f:
            json.dump(blueprint_data, f, indent=2)
        
        console.print(f"[green]✅ Blueprint saved to: {output_file}[/green]")
        return output_file


# CLI Interface
async def main():
    """Main CLI interface for founder interview system"""
    
    # Initialize Anthropic client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set[/red]")
        console.print("Please set your Anthropic API key: export ANTHROPIC_API_KEY=your_key")
        return
    
    client = anthropic.Anthropic(api_key=api_key)
    interview_agent = FounderInterviewAgent(client)
    
    try:
        # Conduct interview
        blueprint = await interview_agent.conduct_interview()
        
        # Save blueprint
        output_file = interview_agent.save_blueprint(blueprint)
        
        console.print(f"\n[bold green]🎉 Success![/bold green]")
        console.print(f"Your business blueprint is ready: {output_file}")
        console.print("\nNext steps:")
        console.print("1. Review the generated blueprint")
        console.print("2. Run the MVP generator to create your startup")
        console.print("3. Deploy and start validating your idea!")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interview cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during interview: {e}[/red]")
        logger.error(f"Interview failed: {e}", exc_info=True)


if __name__ == "__main__":
    import os
    asyncio.run(main())