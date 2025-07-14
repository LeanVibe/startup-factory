#!/usr/bin/env python3
"""
MVP Orchestrator CLI
Command-line interface supporting both interactive and non-interactive modes
"""

import argparse
import asyncio
import json
import sys
from enhanced_mvp_orchestrator import EnhancedMVPOrchestrator

def create_parser():
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(
        description="Enhanced MVP Development Orchestrator with CLI Fallbacks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python mvp_cli.py

  # Non-interactive mode with custom inputs
  python mvp_cli.py --non-interactive --industry fintech --category "AI payments"

  # Non-interactive mode with JSON file
  python mvp_cli.py --non-interactive --input-file inputs.json

  # Quick demo mode
  python mvp_cli.py --demo

  # Show provider status only
  python mvp_cli.py --status-only
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--non-interactive', '-n',
        action='store_true',
        help='Run in non-interactive mode using provided inputs'
    )
    
    parser.add_argument(
        '--demo', '-d',
        action='store_true',
        help='Run demo mode with predefined fintech example'
    )
    
    parser.add_argument(
        '--status-only', '-s',
        action='store_true',
        help='Show provider status only, do not run workflow'
    )
    
    # Input parameters for non-interactive mode
    parser.add_argument(
        '--industry',
        help='Industry for the startup (e.g., fintech, healthtech)'
    )
    
    parser.add_argument(
        '--category',
        help='Category within the industry (e.g., payments, wellness)'
    )
    
    parser.add_argument(
        '--problem',
        help='Problem the startup will solve'
    )
    
    parser.add_argument(
        '--solution',
        help='Proposed solution approach'
    )
    
    parser.add_argument(
        '--target-users',
        help='Target user description'
    )
    
    parser.add_argument(
        '--input-file', '-f',
        help='JSON file containing all input parameters'
    )
    
    # Founder profile parameters
    parser.add_argument(
        '--skills',
        help='Founder key skills'
    )
    
    parser.add_argument(
        '--experience',
        help='Founder relevant experience'
    )
    
    parser.add_argument(
        '--network',
        help='Founder professional network'
    )
    
    parser.add_argument(
        '--resources',
        help='Available resources'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir', '-o',
        default='../mvp_projects',
        help='Output directory for results (default: ../mvp_projects)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Reduce output verbosity'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Increase output verbosity'
    )
    
    return parser

def load_inputs_from_file(file_path):
    """Load inputs from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading input file {file_path}: {e}")
        sys.exit(1)

def get_demo_inputs():
    """Get predefined demo inputs for fintech example"""
    return {
        'industry': 'fintech',
        'category': 'AI-powered fraud detection',
        'problem': 'Financial institutions lose billions annually to payment fraud while legitimate transactions are incorrectly declined',
        'solution': 'Real-time AI fraud detection platform that reduces false positives by 70% while catching 99.5% of actual fraud',
        'target_users': 'Banks, payment processors, fintech companies, and e-commerce platforms with high transaction volumes',
        'founder_profile': {
            'skills': 'Machine learning, financial systems, product management, cybersecurity',
            'experience': '8 years in financial services, 5 years building ML systems at Stripe',
            'network': 'Banking executives, fintech founders, ML engineers, compliance experts',
            'resources': 'Personal savings $200k, co-founder (ML PhD), advisory board of 3 fintech veterans'
        }
    }

def get_brandfocus_demo_inputs():
    """Get BrandFocus AI demo inputs"""
    return {
        'industry': 'professional services',
        'category': 'AI personal branding',
        'problem': 'Professionals struggle to build consistent, authentic personal brands across multiple platforms while maintaining their day jobs',
        'solution': 'AI-powered platform that analyzes user expertise and automatically generates cohesive content strategy, posts, and brand messaging',
        'target_users': 'Mid-career professionals, consultants, and executives looking to establish thought leadership',
        'founder_profile': {
            'skills': 'Software development, UX design, content marketing, AI/ML basics',
            'experience': '5 years as product manager at tech startup, 3 years freelance consultant',
            'network': 'Tech industry contacts, marketing professionals, LinkedIn influencers',
            'resources': 'Personal savings $50k, part-time availability, home office setup'
        }
    }

def collect_inputs_from_args(args):
    """Collect inputs from command line arguments"""
    inputs = {}
    
    # Basic project info
    if args.industry:
        inputs['industry'] = args.industry
    if args.category:
        inputs['category'] = args.category
    if args.problem:
        inputs['problem'] = args.problem
    if args.solution:
        inputs['solution'] = args.solution
    if args.target_users:
        inputs['target_users'] = args.target_users
    
    # Founder profile
    founder_profile = {}
    if args.skills:
        founder_profile['skills'] = args.skills
    if args.experience:
        founder_profile['experience'] = args.experience
    if args.network:
        founder_profile['network'] = args.network
    if args.resources:
        founder_profile['resources'] = args.resources
    
    if founder_profile:
        inputs['founder_profile'] = founder_profile
    
    return inputs

async def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle special modes
    if args.status_only:
        print("🔧 Provider Status Check")
        print("=" * 40)
        orchestrator = EnhancedMVPOrchestrator()
        orchestrator.display_provider_status()
        return
    
    # Determine inputs
    inputs = None
    non_interactive = args.non_interactive or args.demo
    
    if args.input_file:
        inputs = load_inputs_from_file(args.input_file)
        non_interactive = True
    elif args.demo:
        print("🎭 Running Demo Mode: AI Fraud Detection Platform")
        inputs = get_demo_inputs()
    elif args.non_interactive:
        inputs = collect_inputs_from_args(args)
        
        # Validate required inputs for non-interactive mode
        required = ['industry', 'category']
        missing = [key for key in required if key not in inputs]
        if missing:
            print(f"❌ Missing required inputs for non-interactive mode: {missing}")
            print("Use --help for usage examples")
            sys.exit(1)
    
    # Run the orchestrator
    try:
        orchestrator = EnhancedMVPOrchestrator()
        
        if not args.quiet:
            print("🚀 MVP Development Orchestrator")
            print("Enhanced with CLI Fallback Support")
            print("=" * 50)
            
            if non_interactive:
                print("🤖 Non-interactive mode")
            else:
                print("👤 Interactive mode")
        
        await orchestrator.run_full_workflow(
            non_interactive=non_interactive,
            test_inputs=inputs
        )
        
        if not args.quiet:
            print("\n✅ MVP development workflow completed successfully!")
            
    except KeyboardInterrupt:
        print("\n🛑 Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Workflow failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def create_sample_input_file():
    """Create a sample input file for reference"""
    sample_inputs = {
        "industry": "healthtech",
        "category": "AI wellness coaching",
        "problem": "People struggle to maintain healthy habits without personalized guidance and accountability",
        "solution": "AI-powered wellness coach that provides personalized recommendations and real-time motivation",
        "target_users": "Health-conscious individuals, corporate wellness programs, healthcare providers",
        "founder_profile": {
            "skills": "Mobile app development, health science, behavioral psychology",
            "experience": "4 years at fitness startup, MS in Health Informatics",
            "network": "Healthcare professionals, fitness industry, wellness influencers",
            "resources": "Angel funding $150k, co-founder (PhD Psychology), part-time team"
        }
    }
    
    with open('sample_inputs.json', 'w') as f:
        json.dump(sample_inputs, f, indent=2)
    
    print("📄 Sample input file created: sample_inputs.json")

if __name__ == "__main__":
    asyncio.run(main())