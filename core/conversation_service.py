#!/usr/bin/env python3
"""
Conversation Service - Core Service 1/8
Consolidates: founder_interview_system.py, business_blueprint_generator.py
Handles all AI-powered founder conversations and blueprint generation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:  # Allow both package and direct module imports
    from ._compat import Console, Progress, SpinnerColumn, TextColumn
except ImportError:  # pragma: no cover - standalone usage
    from _compat import Console, Progress, SpinnerColumn, TextColumn

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover - exercised when anthropic missing
    anthropic = None  # type: ignore

console = Console()
logger = logging.getLogger(__name__)


class BusinessModel(str, Enum):
    """Business model types"""
    B2B_SAAS = "b2b_saas"
    B2C_SAAS = "b2c_saas" 
    MARKETPLACE = "marketplace"
    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    HEALTHTECH = "healthtech"
    EDTECH = "edtech"
    SOCIAL = "social"
    PRODUCTIVITY = "productivity"
    OTHER = "other"


class IndustryVertical(str, Enum):
    """Industry verticals"""
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    EDUCATION = "education"
    RETAIL = "retail"
    LOGISTICS = "logistics"
    REAL_ESTATE = "real_estate"
    TECHNOLOGY = "technology"
    MEDIA = "media"
    GOVERNMENT = "government"
    OTHER = "other"


@dataclass
class BusinessBlueprint:
    """Consolidated business blueprint from founder conversation"""
    # Core business info
    business_name: str
    description: str
    industry: IndustryVertical
    business_model: BusinessModel
    target_audience: str
    
    # Product details
    key_features: List[str]
    value_proposition: str
    competitive_advantage: str
    
    # Technical requirements
    tech_stack_preferences: Dict[str, str]
    database_requirements: List[str]
    integration_requirements: List[str]
    compliance_requirements: List[str]
    
    # Business intelligence
    monetization_strategy: Dict[str, Any]
    market_analysis: Dict[str, Any]
    user_personas: List[Dict[str, Any]]
    
    # Metadata
    created_at: datetime
    conversation_id: str
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert blueprint to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BusinessBlueprint':
        """Create blueprint from dictionary"""
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class ConversationService:
    """
    Consolidated service for all founder conversation and blueprint generation.
    Replaces founder_interview_system.py and business_blueprint_generator.py
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if anthropic and api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
            except Exception as exc:  # pragma: no cover - guard against bad keys
                logger.warning(f"Anthropic client unavailable: {exc}")
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_blueprint: Optional[BusinessBlueprint] = None
        
        # Intelligent conversation flows by business model
        self.conversation_flows = {
            BusinessModel.B2B_SAAS: self._get_b2b_saas_flow(),
            BusinessModel.MARKETPLACE: self._get_marketplace_flow(),
            BusinessModel.FINTECH: self._get_fintech_flow(),
            BusinessModel.HEALTHTECH: self._get_healthtech_flow(),
        }
    
    async def conduct_founder_interview(self, session_id: str) -> BusinessBlueprint:
        """Conduct intelligent AI conversation with founder"""
        console.print("🤖 Starting AI Architect conversation...")
        
        # Phase 1: Business Discovery
        business_context = await self._discover_business_context()
        
        # Phase 2: Deep Dive with Industry-Specific Questions
        detailed_requirements = await self._conduct_industry_deep_dive(business_context)
        
        # Phase 3: Technical Requirements Analysis
        tech_requirements = await self._analyze_technical_requirements(detailed_requirements)
        
        # Phase 4: Generate Comprehensive Blueprint
        blueprint = await self._generate_business_blueprint(
            business_context, detailed_requirements, tech_requirements, session_id
        )
        
        self.current_blueprint = blueprint
        return blueprint
    
    async def _discover_business_context(self) -> Dict[str, Any]:
        """Phase 1: Discover basic business context"""
        discovery_prompt = """
        You are an expert business analyst and AI architect. Conduct an initial discovery conversation 
        to understand the founder's business idea. Ask 3-4 focused questions to determine:
        
        1. What problem they're solving
        2. Who their target users are  
        3. Their basic business model
        4. Their industry vertical
        
        Be conversational and intelligent in your follow-ups. Don't just ask generic questions.
        """
        
        response = await self._ai_conversation(discovery_prompt)
        
        # Extract structured data from conversation
        context_analysis_prompt = f"""
        Based on this conversation: {response}
        
        Extract and structure the following information as JSON:
        {{
            "problem_statement": "clear description of problem being solved",
            "target_users": "description of target users", 
            "business_model": "one of: b2b_saas, b2c_saas, marketplace, ecommerce, fintech, healthtech, edtech",
            "industry": "one of: healthcare, finance, education, retail, technology",
            "business_name": "proposed or current business name",
            "confidence": 0.8
        }}
        """
        
        context = await self._ai_structured_response(context_analysis_prompt)
        return context
    
    async def _conduct_industry_deep_dive(self, business_context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Industry-specific deep dive questions"""
        business_model = business_context.get('business_model', 'other')
        industry = business_context.get('industry', 'other')
        
        # Get industry-specific conversation flow
        conversation_flow = self.conversation_flows.get(
            BusinessModel(business_model), 
            self._get_generic_flow()
        )
        
        deep_dive_prompt = f"""
        Based on the business context: {json.dumps(business_context, indent=2)}
        
        This is a {business_model} business in the {industry} industry.
        
        Conduct a deep-dive conversation focusing on:
        {json.dumps(conversation_flow, indent=2)}
        
        Ask intelligent follow-up questions and extract detailed requirements.
        """
        
        detailed_response = await self._ai_conversation(deep_dive_prompt)
        
        # Structure the detailed requirements
        requirements_prompt = f"""
        Based on this detailed conversation: {detailed_response}
        
        Extract comprehensive business requirements as JSON:
        {{
            "key_features": ["feature1", "feature2", "feature3"],
            "value_proposition": "clear value prop",
            "competitive_advantage": "what makes this unique",
            "target_personas": [
                {{"name": "persona1", "description": "details", "pain_points": ["pain1", "pain2"]}}
            ],
            "monetization": {{"model": "subscription", "pricing": "details"}},
            "compliance_needs": ["HIPAA", "PCI", "GDPR"]
        }}
        """
        
        detailed_requirements = await self._ai_structured_response(requirements_prompt)
        return detailed_requirements
    
    async def _analyze_technical_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Analyze technical requirements based on business needs"""
        tech_analysis_prompt = f"""
        Based on these business requirements: {json.dumps(requirements, indent=2)}
        
        Determine optimal technical architecture and requirements:
        
        1. Database schema requirements based on business model
        2. API endpoints needed for key features
        3. Third-party integrations required
        4. Compliance and security frameworks
        5. Scalability considerations
        
        Return as structured JSON with technical specifications.
        """
        
        tech_requirements = await self._ai_structured_response(tech_analysis_prompt)
        return tech_requirements
    
    async def _generate_business_blueprint(
        self, 
        context: Dict[str, Any],
        requirements: Dict[str, Any], 
        tech_requirements: Dict[str, Any],
        session_id: str
    ) -> BusinessBlueprint:
        """Phase 4: Generate comprehensive business blueprint"""
        
        blueprint = BusinessBlueprint(
            business_name=context.get('business_name', 'Startup'),
            description=context.get('problem_statement', ''),
            industry=IndustryVertical(context.get('industry', 'other')),
            business_model=BusinessModel(context.get('business_model', 'other')),
            target_audience=context.get('target_users', ''),
            key_features=requirements.get('key_features', []),
            value_proposition=requirements.get('value_proposition', ''),
            competitive_advantage=requirements.get('competitive_advantage', ''),
            tech_stack_preferences=tech_requirements.get('tech_stack', {}),
            database_requirements=tech_requirements.get('database_schema', []),
            integration_requirements=tech_requirements.get('integrations', []),
            compliance_requirements=requirements.get('compliance_needs', []),
            monetization_strategy=requirements.get('monetization', {}),
            market_analysis=requirements.get('market_analysis', {}),
            user_personas=requirements.get('target_personas', []),
            created_at=datetime.utcnow(),
            conversation_id=session_id,
            confidence_score=context.get('confidence', 0.8)
        )
        
        return blueprint
    
    async def _ai_conversation(self, prompt: str) -> str:
        """Conduct AI conversation with Claude"""
        if not self.client:
            # Fallback for tests/demo environments without Anthropic
            return "{\"demo_conversation\": true}"

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"AI conversation error: {e}")
            return f"Error in conversation: {e}"
    
    async def _ai_structured_response(self, prompt: str) -> Dict[str, Any]:
        """Get structured JSON response from AI"""
        try:
            response = await self._ai_conversation(prompt + "\n\nRespond with valid JSON only.")
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"error": "Could not extract JSON from response"}
        except Exception as e:
            logger.error(f"Structured response error: {e}")
            return {"error": str(e)}
    
    def _get_b2b_saas_flow(self) -> Dict[str, Any]:
        """B2B SaaS specific conversation flow"""
        return {
            "business_questions": [
                "What specific business problem does your SaaS solve?",
                "What's your target company size (SMB, Mid-market, Enterprise)?",
                "How do businesses currently solve this problem?",
                "What's your pricing model (per user, per feature, usage-based)?"
            ],
            "technical_focus": ["Multi-tenant architecture", "Role-based permissions", "API integrations"],
            "compliance_considerations": ["SOC2", "GDPR", "Data residency"]
        }
    
    def _get_marketplace_flow(self) -> Dict[str, Any]:
        """Marketplace specific conversation flow"""
        return {
            "business_questions": [
                "What type of marketplace (product, service, digital)?",
                "Who are your supply and demand sides?",
                "How do you solve the chicken-and-egg problem?",
                "What's your commission/fee structure?"
            ],
            "technical_focus": ["Payment processing", "Rating systems", "Search and discovery"],
            "compliance_considerations": ["PCI DSS", "Payment regulations", "Consumer protection"]
        }
    
    def _get_fintech_flow(self) -> Dict[str, Any]:
        """Fintech specific conversation flow"""
        return {
            "business_questions": [
                "What financial services are you providing?",
                "Are you handling money movement?",
                "What licenses/regulations apply?",
                "What's your fraud prevention strategy?"
            ],
            "technical_focus": ["PCI compliance", "Bank integrations", "Fraud detection"],
            "compliance_considerations": ["PCI DSS", "SOX", "Regional financial regulations"]
        }
    
    def _get_healthtech_flow(self) -> Dict[str, Any]:
        """Healthcare specific conversation flow"""
        return {
            "business_questions": [
                "Are you handling PHI (protected health information)?",
                "What healthcare providers will use this?",
                "Do you need FDA approval?",
                "What clinical workflows does this integrate with?"
            ],
            "technical_focus": ["HIPAA compliance", "HL7/FHIR", "Clinical integrations"],
            "compliance_considerations": ["HIPAA", "FDA", "HITECH", "State regulations"]
        }
    
    def _get_generic_flow(self) -> Dict[str, Any]:
        """Generic conversation flow for other business types"""
        return {
            "business_questions": [
                "What makes your solution unique?",
                "How do users discover and use your product?",
                "What's your go-to-market strategy?",
                "How do you plan to monetize?"
            ],
            "technical_focus": ["Scalability", "User experience", "Performance"],
            "compliance_considerations": ["GDPR", "Basic data protection"]
        }
    
    async def save_blueprint(self, blueprint: BusinessBlueprint, file_path: str) -> bool:
        """Save blueprint to file"""
        try:
            blueprint_data = blueprint.to_dict()
            # Convert datetime to string for JSON serialization
            blueprint_data['created_at'] = blueprint.created_at.isoformat()
            
            with open(file_path, 'w') as f:
                json.dump(blueprint_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving blueprint: {e}")
            return False
    
    async def load_blueprint(self, file_path: str) -> Optional[BusinessBlueprint]:
        """Load blueprint from file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return BusinessBlueprint.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading blueprint: {e}")
            return None


# Example usage
async def main():
    """Example usage of ConversationService"""
    conversation_service = ConversationService()
    
    # Conduct founder interview
    blueprint = await conversation_service.conduct_founder_interview("test_session_123")
    
    console.print(f"Generated blueprint for: {blueprint.business_name}")
    console.print(f"Industry: {blueprint.industry}")
    console.print(f"Business Model: {blueprint.business_model}")
    console.print(f"Key Features: {blueprint.key_features}")


if __name__ == "__main__":
    asyncio.run(main())
