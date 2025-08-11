#!/usr/bin/env python3
"""
Complete MVP Generation Demo - Non-Interactive Version
Demonstrates the full Startup Factory pipeline without user input.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

# Import demo components
from demo_mvp_generator import DemoMVPGenerator, MOCK_BUSINESS_SCENARIOS

async def run_automated_demo():
    """Run the complete demo automatically for all scenarios"""
    
    print("🚀 STARTUP FACTORY - AUTOMATED DEMO")
    print("=" * 50)
    
    demo = DemoMVPGenerator()
    results = []
    
    for i, (scenario_name, scenario) in enumerate(MOCK_BUSINESS_SCENARIOS.items(), 1):
        print(f"\n🎯 DEMO {i}/3: {scenario_name.upper()}")
        print("-" * 30)
        print(f"Business Idea: {scenario['business_idea']}")
        print(f"Target Market: {scenario['target_market']}")
        
        start_time = time.time()
        
        # Override the interactive parts for automated demo
        demo_instance = AutomatedDemoGenerator(scenario)
        project_path = await demo_instance.run_automated_generation()
        
        generation_time = time.time() - start_time
        
        results.append({
            "scenario": scenario_name,
            "project_path": str(project_path),
            "generation_time": generation_time,
            "files_created": len(list(project_path.rglob('*')))
        })
        
        print(f"✅ Generated: {project_path}")
        print(f"⏱️  Time: {generation_time:.2f} seconds")
        print(f"📁 Files: {len(list(project_path.rglob('*')))} created")
    
    # Show summary
    print("\n🎉 ALL DEMOS COMPLETED")
    print("=" * 50)
    
    total_time = sum(r["generation_time"] for r in results)
    total_files = sum(r["files_created"] for r in results)
    
    print(f"Total Projects Generated: {len(results)}")
    print(f"Total Time: {total_time:.2f} seconds")
    print(f"Average Time per MVP: {total_time / len(results):.2f} seconds")
    print(f"Total Files Created: {total_files}")
    print(f"25-Minute Promise: ✅ VALIDATED (simulated)")
    
    print("\n📊 DETAILED RESULTS:")
    for result in results:
        print(f"  • {result['scenario']}: {result['generation_time']:.2f}s ({result['files_created']} files)")
    
    print(f"\n📁 Generated MVPs located in: {demo.output_dir.absolute()}")
    
    return results

class AutomatedDemoGenerator:
    """Automated version of the demo generator for CI/testing"""
    
    def __init__(self, scenario):
        self.scenario = scenario
        self.session_start = datetime.now()
        self.output_dir = Path("demo_generated_mvps")
        self.output_dir.mkdir(exist_ok=True)
        
    async def run_automated_generation(self):
        """Run the complete generation without user interaction"""
        
        # Import the actual components
        from test_complete_mvp_pipeline import MockFounderInterviewSimulator, MockCodeGenerator
        
        print("  🤖 Conducting founder interview...")
        interview_sim = MockFounderInterviewSimulator(self.scenario)
        blueprint = await interview_sim.simulate_interview_responses()
        
        print("  🧠 Analyzing business model...")
        await asyncio.sleep(0.1)  # Simulate analysis
        
        print("  ⚡ Generating MVP code...")
        code_generator = MockCodeGenerator(blueprint)
        generated_files = await code_generator.generate_mvp_code()
        
        print("  🔧 Creating project structure...")
        project_path = await self._create_project(generated_files, blueprint)
        
        return project_path
    
    async def _create_project(self, generated_files, blueprint):
        """Create the MVP project"""
        
        # Generate unique project name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        business_name = self.scenario["industry"]
        project_name = f"{business_name}_mvp_{timestamp}"
        
        project_path = self.output_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Write all generated files
        for file_path, content in generated_files.items():
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        # Add additional project files
        await self._add_project_extras(project_path, blueprint)
        
        return project_path
    
    async def _add_project_extras(self, project_path, blueprint):
        """Add additional project files"""
        
        # Create package.json for frontend
        package_json = {
            "name": f"{project_path.name}-frontend",
            "version": "1.0.0",
            "private": True,
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test"
            }
        }
        
        frontend_dir = project_path / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        (frontend_dir / "package.json").write_text(json.dumps(package_json, indent=2))
        
        # Create requirements.txt for backend
        requirements = """fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
python-multipart==0.0.6
"""
        
        backend_dir = project_path / "backend"
        backend_dir.mkdir(exist_ok=True)
        (backend_dir / "requirements.txt").write_text(requirements)
        
        # Create Dockerfile for backend
        dockerfile = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        (backend_dir / "Dockerfile").write_text(dockerfile)
        
        # Create startup script
        startup_script = """#!/bin/bash
echo "🚀 Starting MVP..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Database: PostgreSQL on localhost:5432"
echo ""
echo "Run: docker-compose up -d"
"""
        (project_path / "start.sh").write_text(startup_script)

if __name__ == "__main__":
    asyncio.run(run_automated_demo())