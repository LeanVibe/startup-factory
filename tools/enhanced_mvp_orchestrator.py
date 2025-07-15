#!/usr/bin/env python3
"""
Enhanced MVP Development Orchestrator with CLI Fallbacks
Main agent-led orchestration: comprehensive Python script with fallback scenarios for missing API keys.

Transition: Claude code orchestration replaced by main agent leadership. All escalation protocols, provider assignments, and human-in-the-loop gates now reference main agent as the orchestrator.

FALLBACK MECHANISMS:
- OpenAI missing → Use OpenCode CLI in non-interactive mode
- Anthropic missing → Use claude-p for non-anthropic search
- Perplexity missing → Use Gemini CLI with -print flag

USAGE:
    python enhanced_mvp_orchestrator.py

FEATURES:
    - Automatic fallback to CLI tools when API keys unavailable
    - Cost tracking across all providers and tools
    - Enhanced error handling and recovery
    - CLI tool integration for seamless operation
"""

import os
import json
import yaml
import asyncio
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

# Try to import API libraries, but don't fail if missing
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    OPENCODE_CLI = "opencode_cli"
    CLAUDE_P_CLI = "claude_p_cli"
    CLAUDE_CODE_CLI = "claude_code_cli"
    GEMINI_CLI = "gemini_cli"


class FallbackMode(str, Enum):
    API = "api"
    CLI = "cli"
    HYBRID = "hybrid"


@dataclass
class ProviderConfig:
    """Configuration for each AI provider including fallbacks"""

    name: str
    primary_mode: FallbackMode
    fallback_mode: Optional[FallbackMode]
    api_key_env: str
    cli_command: Optional[str]
    cost_per_1k_input: float
    cost_per_1k_output: float
    available: bool = True


class EnhancedAPIManager:
    """Enhanced API manager with CLI fallbacks"""

    def __init__(self, config_path: str = "../config.yaml"):
        self.config_path = config_path
        self.load_config()
        self.setup_providers()
        self.total_costs = {provider: 0.0 for provider in AIProvider}

    def load_config(self):
        """Load configuration from YAML file"""
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)

    def setup_providers(self):
        """Set up provider configurations with fallback detection"""
        self.providers = {
            AIProvider.OPENAI: ProviderConfig(
                name="OpenAI",
                primary_mode=FallbackMode.API,
                fallback_mode=FallbackMode.CLI,
                api_key_env="OPENAI_API_KEY",
                cli_command="opencode",
                cost_per_1k_input=self.config.get("openai_input_cost_per_1k", 0.01),
                cost_per_1k_output=self.config.get("openai_output_cost_per_1k", 0.03),
                available=OPENAI_AVAILABLE and bool(os.getenv("OPENAI_API_KEY")),
            ),
            AIProvider.ANTHROPIC: ProviderConfig(
                name="Anthropic",
                primary_mode=FallbackMode.API,
                fallback_mode=FallbackMode.CLI,
                api_key_env="ANTHROPIC_API_KEY",
                cli_command="claude",  # Claude Code CLI is the primary fallback
                cost_per_1k_input=self.config.get("anthropic_input_cost_per_1k", 0.015),
                cost_per_1k_output=self.config.get(
                    "anthropic_output_cost_per_1k", 0.075
                ),
                available=ANTHROPIC_AVAILABLE and bool(os.getenv("ANTHROPIC_API_KEY")),
            ),
            AIProvider.PERPLEXITY: ProviderConfig(
                name="Perplexity",
                primary_mode=FallbackMode.API,
                fallback_mode=FallbackMode.CLI,
                api_key_env="PERPLEXITY_API_KEY",
                cli_command="gemini",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                available=bool(os.getenv("PERPLEXITY_API_KEY")),
            ),
        }

        # Initialize API clients for available providers
        if self.providers[AIProvider.OPENAI].available:
            self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if self.providers[AIProvider.ANTHROPIC].available:
            self.anthropic_client = anthropic.AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )

    def check_cli_availability(self, command: str) -> bool:
        """Check if CLI tool is available"""
        try:
            result = subprocess.run(
                [command, "--help"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def call_openai_api(
        self, prompt: str, max_tokens: int = 4000
    ) -> Tuple[str, float]:
        """Call OpenAI API directly"""
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        cost = self.calculate_openai_cost(response.usage)
        return content, cost

    async def call_openai_cli_fallback(self, prompt: str) -> Tuple[str, float]:
        """Fallback to OpenCode CLI when OpenAI API key is missing"""
        print("🔄 OpenAI API key not available, using OpenCode CLI fallback...")

        # Check if opencode CLI is available
        if not self.check_cli_availability("opencode"):
            raise Exception(
                "OpenCode CLI not available. Please install or provide OpenAI API key."
            )

        # Create temporary file for prompt
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Use OpenCode CLI in non-interactive mode
            cmd = [
                "opencode",
                "--non-interactive",
                "--input",
                prompt_file,
                "--output",
                "text",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise Exception(f"OpenCode CLI failed: {result.stderr}")

            # Estimate cost (rough approximation)
            estimated_tokens = len(prompt.split()) + len(result.stdout.split())
            cost = estimated_tokens * (
                self.providers[AIProvider.OPENAI].cost_per_1k_input / 1000
            )

            return result.stdout.strip(), cost

        finally:
            # Clean up temporary file
            os.unlink(prompt_file)

    async def call_anthropic_api(
        self, prompt: str, max_tokens: int = 4000
    ) -> Tuple[str, float]:
        """Call Anthropic API directly"""
        response = await self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.content[0].text
        cost = self.calculate_anthropic_cost(response.usage)
        return content, cost

    async def call_anthropic_cli_fallback(self, prompt: str) -> Tuple[str, float]:
        """Fallback to Claude Code CLI when Anthropic API key is missing"""
        print("🔄 Anthropic API key not available, using Claude Code CLI fallback...")

        # Check if Claude Code CLI is available first
        if self.check_cli_availability("claude"):
            return await self.call_claude_code_cli(prompt)

        # Fallback to claude-p if Claude Code CLI not available
        if self.check_cli_availability("claude-p"):
            return await self.call_claude_p_cli(prompt)

        raise Exception(
            "No Claude CLI tools available. Please install Claude Code CLI or provide Anthropic API key."
        )

    async def call_claude_code_cli(self, prompt: str) -> Tuple[str, float]:
        """Use Claude Code CLI for code generation and analysis"""
        print("🤖 Using Claude Code CLI...")

        # Create temporary file for prompt
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(f"# Task\n\n{prompt}\n\n")
            f.write(
                "Please provide a comprehensive response following the requirements above."
            )
            prompt_file = f.name

        try:
            # Use Claude Code CLI with file input
            cmd = ["claude", prompt_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise Exception(f"Claude Code CLI failed: {result.stderr}")

            # Claude Code CLI typically provides high-quality responses
            # Estimate cost based on premium Claude usage
            estimated_tokens = len(prompt.split()) + len(result.stdout.split())
            cost = (
                estimated_tokens
                * (self.providers[AIProvider.ANTHROPIC].cost_per_1k_input / 1000)
                * 0.8
            )  # Slight discount for CLI

            return result.stdout.strip(), cost

        except subprocess.TimeoutExpired:
            raise Exception("Claude Code CLI timed out after 5 minutes")
        finally:
            # Clean up temporary file
            os.unlink(prompt_file)

    async def call_claude_p_cli(self, prompt: str) -> Tuple[str, float]:
        """Use claude-p CLI as secondary fallback"""
        print("🔄 Using claude-p CLI as secondary fallback...")

        try:
            # Use claude-p for search functionality
            cmd = ["claude-p", "--search", "--query", prompt, "--format", "text"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise Exception(f"claude-p CLI failed: {result.stderr}")

            # Estimate cost (rough approximation)
            estimated_tokens = len(prompt.split()) + len(result.stdout.split())
            cost = (
                estimated_tokens
                * (self.providers[AIProvider.ANTHROPIC].cost_per_1k_input / 1000)
                * 0.5
            )  # Lower cost for search

            return result.stdout.strip(), cost

        except subprocess.TimeoutExpired:
            raise Exception("claude-p CLI timed out after 5 minutes")

    async def call_perplexity_api(self, prompt: str) -> Tuple[str, float]:
        """Call Perplexity API directly"""
        if not HTTPX_AVAILABLE:
            raise Exception("httpx library required for Perplexity API")

        api_key = os.getenv("PERPLEXITY_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0,
            )

            if response.status_code != 200:
                raise Exception(f"Perplexity API error: {response.status_code}")

            result = response.json()
            content = result["choices"][0]["message"]["content"]
            cost = self.config.get("perplexity_cost_per_request", 0.005)

            return content, cost

    async def call_perplexity_cli_fallback(self, prompt: str) -> Tuple[str, float]:
        """Fallback to Gemini CLI when Perplexity API key is missing"""
        print("🔄 Perplexity API key not available, using Gemini CLI fallback...")

        # Check if gemini CLI is available
        if not self.check_cli_availability("gemini"):
            raise Exception(
                "Gemini CLI not available. Please install or provide Perplexity API key."
            )

        # Create temporary file for prompt
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(f"# Research Task\n\n{prompt}\n\n")
            f.write("Please provide comprehensive research and analysis on this topic.")
            prompt_file = f.name

        try:
            # Use Gemini CLI with prompt parameter
            cmd = ["gemini", "-p", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise Exception(f"Gemini CLI failed: {result.stderr}")

            # Estimate cost (Gemini may be free or very low cost)
            cost = 0.001  # Minimal cost estimate

            return result.stdout.strip(), cost

        except subprocess.TimeoutExpired:
            raise Exception("Gemini CLI timed out after 5 minutes")
        finally:
            # Clean up temporary file
            os.unlink(prompt_file)

    async def call_provider(
        self, provider: AIProvider, prompt: str, max_tokens: int = 4000
    ) -> Tuple[str, float]:
        """Call provider with automatic fallback to CLI if API unavailable"""
        provider_config = self.providers[provider]

        try:
            # Try API first if available
            if (
                provider_config.available
                and provider_config.primary_mode == FallbackMode.API
            ):
                if provider == AIProvider.OPENAI:
                    return await self.call_openai_api(prompt, max_tokens)
                elif provider == AIProvider.ANTHROPIC:
                    return await self.call_anthropic_api(prompt, max_tokens)
                elif provider == AIProvider.PERPLEXITY:
                    return await self.call_perplexity_api(prompt)

            # Fallback to CLI if API not available or failed
            print(f"🔄 Falling back to CLI for {provider_config.name}...")

            if provider == AIProvider.OPENAI:
                return await self.call_openai_cli_fallback(prompt)
            elif provider == AIProvider.ANTHROPIC:
                return await self.call_anthropic_cli_fallback(prompt)
            elif provider == AIProvider.PERPLEXITY:
                return await self.call_perplexity_cli_fallback(prompt)

        except Exception as e:
            print(f"❌ Error with {provider_config.name}: {str(e)}")

            # Try one more fallback if available
            if provider_config.fallback_mode == FallbackMode.CLI:
                print(f"🔄 Attempting final CLI fallback for {provider_config.name}...")
                try:
                    if provider == AIProvider.OPENAI:
                        return await self.call_openai_cli_fallback(prompt)
                    elif provider == AIProvider.ANTHROPIC:
                        return await self.call_anthropic_cli_fallback(prompt)
                    elif provider == AIProvider.PERPLEXITY:
                        return await self.call_perplexity_cli_fallback(prompt)
                except Exception as fallback_error:
                    print(f"❌ CLI fallback also failed: {str(fallback_error)}")

            raise Exception(f"All methods failed for {provider_config.name}: {str(e)}")

    def calculate_openai_cost(self, usage) -> float:
        """Calculate OpenAI API cost"""
        input_cost = usage.prompt_tokens * (
            self.providers[AIProvider.OPENAI].cost_per_1k_input / 1000
        )
        output_cost = usage.completion_tokens * (
            self.providers[AIProvider.OPENAI].cost_per_1k_output / 1000
        )
        return input_cost + output_cost

    def calculate_anthropic_cost(self, usage) -> float:
        """Calculate Anthropic API cost"""
        input_cost = usage.input_tokens * (
            self.providers[AIProvider.ANTHROPIC].cost_per_1k_input / 1000
        )
        output_cost = usage.output_tokens * (
            self.providers[AIProvider.ANTHROPIC].cost_per_1k_output / 1000
        )
        return input_cost + output_cost

    def get_total_cost(self) -> float:
        """Get total cost across all providers"""
        return sum(self.total_costs.values())

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by provider"""
        return dict(self.total_costs)


class EnhancedMVPOrchestrator:
    """Enhanced MVP orchestrator with CLI fallbacks"""

    def __init__(self, config_path: str = "../config.yaml"):
        self.api_manager = EnhancedAPIManager(config_path)
        self.project_data = {}

    async def run_market_research(self, industry: str, category: str) -> Dict[str, Any]:
        """Run market research with Perplexity (or Gemini CLI fallback)"""
        print("🔍 Running market research...")

        prompt = f"""Analyze the market opportunity for {industry} focusing on {category}:

1. Market size and growth projections (2024-2027)
2. Top 10 emerging trends with supporting data
3. Underserved customer segments
4. Technology enablers creating new opportunities
5. Regulatory changes affecting the market

Requirements:
- Include specific statistics and sources
- Focus on B2B/B2C opportunities under $10M ARR
- Highlight gaps where solo founders can compete
- Provide revenue model examples for each opportunity

Format: Structured markdown with clear sections and bullet points"""

        try:
            result, cost = await self.api_manager.call_provider(
                AIProvider.PERPLEXITY, prompt
            )
            self.api_manager.total_costs[AIProvider.PERPLEXITY] += cost
            print(f"💰 Market research cost: ${cost:.4f}")
            return {"content": result, "cost": cost, "provider": "perplexity"}
        except Exception as e:
            print(f"❌ Market research failed: {str(e)}")
            return {
                "content": f"Market research failed: {str(e)}",
                "cost": 0.0,
                "provider": "error",
            }

    async def run_founder_analysis(
        self, market_data: str, founder_profile: Dict[str, str]
    ) -> Dict[str, Any]:
        """Run founder analysis with Anthropic (or claude-p fallback)"""
        print("👤 Analyzing founder-market fit...")

        prompt = f"""<analysis_request>
<founder_profile>
Skills: {founder_profile.get('skills', 'Not specified')}
Experience: {founder_profile.get('experience', 'Not specified')}
Network: {founder_profile.get('network', 'Not specified')}
Resources: {founder_profile.get('resources', 'Not specified')}
</founder_profile>

<market_opportunities>
{market_data}
</market_opportunities>

Evaluate founder-market fit for each opportunity:
1. Score each opportunity (1-10) on skill alignment, passion sustainability, competitive advantage
2. Provide specific recommendations for the top 2 matches
3. List skill gaps and how to address them
4. Suggest initial customer segments to target

Output format: Scoring matrix followed by detailed recommendations
</analysis_request>"""

        try:
            result, cost = await self.api_manager.call_provider(
                AIProvider.ANTHROPIC, prompt
            )
            self.api_manager.total_costs[AIProvider.ANTHROPIC] += cost
            print(f"💰 Founder analysis cost: ${cost:.4f}")
            return {"content": result, "cost": cost, "provider": "anthropic"}
        except Exception as e:
            print(f"❌ Founder analysis failed: {str(e)}")
            return {
                "content": f"Founder analysis failed: {str(e)}",
                "cost": 0.0,
                "provider": "error",
            }

    async def generate_mvp_spec(
        self, problem: str, solution: str, target_users: str
    ) -> Dict[str, Any]:
        """Generate MVP specification with OpenAI (or OpenCode CLI fallback)"""
        print("📋 Generating MVP specification...")

        prompt = f"""<mvp_specification_request>
<solution>
Problem: {problem}
Solution: {solution}
Target Users: {target_users}
</solution>

<constraints>
Development time: 4 weeks maximum
Technical stack: FastAPI + React/Vue
</constraints>

Create comprehensive MVP specification:

1. CORE FEATURES (max 3) - User story format with acceptance criteria
2. USER JOURNEY - Onboarding flow, core workflow, success metrics
3. TECHNICAL ARCHITECTURE - System components, data model, API structure
4. DESIGN REQUIREMENTS - UI components, responsive breakpoints
5. LAUNCH CRITERIA - Quality benchmarks, performance targets

Format: Structured markdown with clear sections
</mvp_specification_request>"""

        try:
            result, cost = await self.api_manager.call_provider(
                AIProvider.OPENAI, prompt
            )
            self.api_manager.total_costs[AIProvider.OPENAI] += cost
            print(f"💰 MVP specification cost: ${cost:.4f}")
            return {"content": result, "cost": cost, "provider": "openai"}
        except Exception as e:
            print(f"❌ MVP specification failed: {str(e)}")
            return {
                "content": f"MVP specification failed: {str(e)}",
                "cost": 0.0,
                "provider": "error",
            }

    def display_provider_status(self):
        """Display status of all providers and fallbacks"""
        print("\n🔧 Provider Status Check")
        print("=" * 50)

        for provider, config in self.api_manager.providers.items():
            api_key_status = "✅" if config.available else "❌"
            cli_status = (
                "✅"
                if self.api_manager.check_cli_availability(config.cli_command)
                else "❌"
            )

            print(f"{config.name}:")
            print(f"  API Key: {api_key_status} ({config.api_key_env})")
            if config.cli_command:
                print(f"  CLI Tool: {cli_status} ({config.cli_command})")
            print(f"  Primary: {config.primary_mode.value}")
            if config.fallback_mode:
                print(f"  Fallback: {config.fallback_mode.value}")
            print()

    async def run_full_workflow(self, non_interactive=False, test_inputs=None):
        """Run the complete MVP development workflow with fallbacks"""
        print("🚀 Starting Enhanced MVP Development Workflow")
        print("=" * 60)

        # Display provider status
        self.display_provider_status()

        if non_interactive and test_inputs:
            # Use provided test inputs
            industry = test_inputs.get("industry", "fintech")
            category = test_inputs.get("category", "AI payments")
            founder_profile = test_inputs.get(
                "founder_profile",
                {
                    "skills": "Software development, product management",
                    "experience": "5 years in fintech, 3 years as PM",
                    "network": "Financial services, tech startups",
                    "resources": "Personal savings $100k, full-time availability",
                },
            )

            print(f"📋 Using non-interactive mode:")
            print(f"  Industry: {industry}")
            print(f"  Category: {category}")
            print(f"  Founder Profile: {founder_profile}")
        else:
            # Interactive mode
            try:
                industry = input(
                    "Enter industry (e.g., 'fintech', 'healthtech'): "
                ).strip()
                category = input(
                    "Enter category (e.g., 'payments', 'wellness'): "
                ).strip()

                founder_profile = {
                    "skills": input("Your key skills: ").strip(),
                    "experience": input("Relevant experience: ").strip(),
                    "network": input("Professional network: ").strip(),
                    "resources": input("Available resources: ").strip(),
                }
            except (EOFError, KeyboardInterrupt):
                print("\n🤖 Interactive input not available, switching to demo mode...")
                industry = "AI-powered fintech"
                category = "smart payment analytics"
                founder_profile = {
                    "skills": "Machine learning, financial modeling, product management",
                    "experience": "7 years in fintech, 4 years building ML systems",
                    "network": "Banking executives, fintech founders, ML engineers",
                    "resources": "Series A funding $2M, team of 5 engineers",
                }
                print(f"📋 Demo inputs:")
                print(f"  Industry: {industry}")
                print(f"  Category: {category}")

        print("\n" + "=" * 60)
        print("🎯 Executing Workflow Phases")
        print("=" * 60)

        # Phase 1: Market Research
        market_data = await self.run_market_research(industry, category)
        print(f"✅ Market research completed using {market_data['provider']}")

        # Phase 2: Founder Analysis
        founder_analysis = await self.run_founder_analysis(
            market_data["content"], founder_profile
        )
        print(f"✅ Founder analysis completed using {founder_analysis['provider']}")

        # Phase 3: MVP Specification
        print("\n📝 Phase 3: MVP Specification")
        if non_interactive and test_inputs:
            problem = test_inputs.get(
                "problem", "Complex payment processing and fraud detection"
            )
            solution = test_inputs.get(
                "solution", "AI-powered real-time payment analytics and risk assessment"
            )
            target_users = test_inputs.get(
                "target_users",
                "Financial institutions, payment processors, fintech companies",
            )
            print(f"  Problem: {problem}")
            print(f"  Solution: {solution}")
            print(f"  Target Users: {target_users}")
        else:
            try:
                print("Based on the analysis, please provide:")
                problem = input("Problem to solve: ").strip()
                solution = input("Proposed solution: ").strip()
                target_users = input("Target users: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("🤖 Using demo specification inputs...")
                problem = "Financial institutions need real-time fraud detection and payment optimization"
                solution = "AI-powered analytics platform that processes payment data in real-time to detect fraud patterns and optimize transaction success rates"
                target_users = "Banks, payment processors, fintech companies, and e-commerce platforms processing high-volume transactions"
                print(f"  Problem: {problem}")
                print(f"  Solution: {solution}")
                print(f"  Target Users: {target_users}")

        mvp_spec = await self.generate_mvp_spec(problem, solution, target_users)
        print(f"✅ MVP specification completed using {mvp_spec['provider']}")

        # Summary
        total_cost = self.api_manager.get_total_cost()
        cost_breakdown = self.api_manager.get_cost_breakdown()

        print("\n" + "=" * 60)
        print("🎉 Workflow Complete!")
        print("=" * 60)
        print(f"💰 Total Cost: ${total_cost:.4f}")
        print("💳 Cost Breakdown:")
        for provider, cost in cost_breakdown.items():
            if cost > 0:
                print(f"  {provider.value}: ${cost:.4f}")

        # Save results
        results = {
            "timestamp": datetime.now().isoformat(),
            "industry": industry,
            "category": category,
            "founder_profile": founder_profile,
            "market_research": market_data,
            "founder_analysis": founder_analysis,
            "mvp_specification": mvp_spec,
            "total_cost": total_cost,
            "cost_breakdown": cost_breakdown,
        }

        # Save to file
        output_dir = Path("../mvp_projects")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{industry}_{category}_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"📄 Results saved to: {output_file}")

        return results


async def main():
    """Main entry point for enhanced MVP orchestrator"""
    try:
        orchestrator = EnhancedMVPOrchestrator()
        await orchestrator.run_full_workflow()
    except KeyboardInterrupt:
        print("\n🛑 Workflow interrupted by user")
    except Exception as e:
        print(f"\n❌ Workflow failed: {str(e)}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
