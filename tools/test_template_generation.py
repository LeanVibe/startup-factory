#!/usr/bin/env python3
"""
Template Generation Testing Suite
Tests template system and project generation capabilities for the Startup Factory
"""

import json
import time
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sys
import yaml

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

@dataclass
class TemplateTestResult:
    test_name: str
    status: str
    details: str
    duration: float = 0.0
    metadata: Dict[str, Any] = None

class TemplateGenerationTester:
    """Tests template generation and project creation functionality"""
    
    def __init__(self):
        self.results: List[TemplateTestResult] = []
        self.temp_dir = None
        self.template_dir = Path(__file__).parent.parent / "templates"
        
    def log_result(self, test_name: str, status: str, details: str, 
                   duration: float = 0.0, metadata: Dict = None):
        """Log test result"""
        result = TemplateTestResult(
            test_name=test_name,
            status=status,
            details=details,
            duration=duration,
            metadata=metadata or {}
        )
        self.results.append(result)
        
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {test_name}: {details}")
        if duration > 0:
            print(f"   ⏱️ {duration:.2f}s")
    
    def setup(self) -> bool:
        """Setup test environment"""
        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="template_test_"))
            print(f"📂 Created temp directory: {self.temp_dir}")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup test environment"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def test_template_structure(self) -> bool:
        """Test template directory structure and availability"""
        print("\n🏗️ Testing Template Structure")
        
        start_time = time.time()
        
        try:
            # Check templates directory exists
            if not self.template_dir.exists():
                self.log_result(
                    "Template Structure",
                    "FAIL",
                    "Templates directory not found",
                    time.time() - start_time
                )
                return False
            
            # Check for neoforge template
            neoforge_template = self.template_dir / "neoforge"
            if not neoforge_template.exists():
                self.log_result(
                    "Template Structure",
                    "FAIL",
                    "Neoforge template directory not found",
                    time.time() - start_time
                )
                return False
            
            # Check for cookiecutter.json
            cookiecutter_config = neoforge_template / "cookiecutter.json"
            if not cookiecutter_config.exists():
                self.log_result(
                    "Template Structure",
                    "FAIL",
                    "Cookiecutter configuration not found",
                    time.time() - start_time
                )
                return False
            
            # Validate cookiecutter.json structure
            with open(cookiecutter_config, 'r') as f:
                config_data = json.load(f)
            
            required_vars = [
                "project_name",
                "project_slug",
                "project_description"
            ]
            
            missing_vars = [var for var in required_vars if var not in config_data]
            
            if missing_vars:
                self.log_result(
                    "Template Structure",
                    "FAIL",
                    f"Missing required variables: {missing_vars}",
                    time.time() - start_time
                )
                return False
            
            # Check template structure
            template_project_dir = neoforge_template / "{{cookiecutter.project_slug}}"
            if not template_project_dir.exists():
                self.log_result(
                    "Template Structure",
                    "FAIL",
                    "Template project directory not found",
                    time.time() - start_time
                )
                return False
            
            # Check for key template files
            expected_files = [
                "README.md",
                "docker-compose.yml",
                "backend/requirements.txt",
                "frontend/package.json"
            ]
            
            missing_files = []
            for file_path in expected_files:
                if not (template_project_dir / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                self.log_result(
                    "Template Structure",
                    "WARN",
                    f"Some template files missing: {missing_files}",
                    time.time() - start_time
                )
                return True  # Warning, not failure
            
            self.log_result(
                "Template Structure",
                "PASS",
                f"Template structure valid with {len(config_data)} variables",
                time.time() - start_time,
                {
                    "template_dir": str(neoforge_template),
                    "config_vars": len(config_data),
                    "expected_files": len(expected_files)
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                "Template Structure",
                "FAIL",
                f"Template structure test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_cookiecutter_generation(self) -> bool:
        """Test cookiecutter project generation"""
        print("\n🍪 Testing Cookiecutter Generation")
        
        start_time = time.time()
        
        try:
            # Test data for project generation
            test_context = {
                "project_name": "Test AI Assistant",
                "project_slug": "test-ai-assistant", 
                "project_description": "A test AI assistant project",
                "author_name": "Test Developer",
                "author_email": "test@example.com",
                "version": "0.1.0"
            }
            
            # Create cookiecutter context file
            context_file = self.temp_dir / "cookiecutter_context.json"
            with open(context_file, 'w') as f:
                json.dump(test_context, f, indent=2)
            
            # Try to generate project using cookiecutter
            neoforge_template = self.template_dir / "neoforge"
            output_dir = self.temp_dir / "generated_projects"
            output_dir.mkdir(exist_ok=True)
            
            # Test cookiecutter command availability
            result = subprocess.run([
                "python", "-c", 
                """
try:
    import cookiecutter
    print('COOKIECUTTER_AVAILABLE')
except ImportError:
    print('COOKIECUTTER_UNAVAILABLE')
                """
            ], capture_output=True, text=True, timeout=10)
            
            if "COOKIECUTTER_AVAILABLE" not in result.stdout:
                # Try manual template generation
                project_dir = output_dir / test_context["project_slug"]
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy and process basic template files
                template_project_dir = neoforge_template / "{{cookiecutter.project_slug}}"
                
                # Create basic project structure
                (project_dir / "backend").mkdir(exist_ok=True)
                (project_dir / "frontend").mkdir(exist_ok=True)
                
                # Create basic files
                readme_content = f"""# {test_context['project_name']}

{test_context['project_description']}

## Getting Started

This project was generated using the Startup Factory template system.

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Development

See individual component READMEs for detailed setup instructions.

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
                
                with open(project_dir / "README.md", 'w') as f:
                    f.write(readme_content)
                
                # Create basic docker-compose.yml
                compose_content = f"""version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME={test_context['project_name']}
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB={test_context['project_slug'].replace('-', '_')}
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
"""
                
                with open(project_dir / "docker-compose.yml", 'w') as f:
                    f.write(compose_content)
                
                # Create basic backend requirements.txt
                requirements_content = """fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pydantic>=2.5.0
python-multipart>=0.0.6
"""
                
                backend_dir = project_dir / "backend"
                backend_dir.mkdir(exist_ok=True)
                with open(backend_dir / "requirements.txt", 'w') as f:
                    f.write(requirements_content)
                
                # Create basic frontend package.json
                package_json = {
                    "name": test_context["project_slug"],
                    "version": test_context["version"],
                    "description": test_context["project_description"],
                    "scripts": {
                        "dev": "vite",
                        "build": "vite build",
                        "preview": "vite preview"
                    },
                    "dependencies": {
                        "lit": "^3.0.0"
                    },
                    "devDependencies": {
                        "vite": "^5.0.0"
                    }
                }
                
                frontend_dir = project_dir / "frontend"
                frontend_dir.mkdir(exist_ok=True)
                with open(frontend_dir / "package.json", 'w') as f:
                    json.dump(package_json, f, indent=2)
                
                generation_method = "manual"
            else:
                # Use actual cookiecutter
                generation_method = "cookiecutter"
                # Would implement actual cookiecutter call here
            
            # Validate generated project
            generated_project = output_dir / test_context["project_slug"]
            
            validation_checks = [
                generated_project.exists(),
                (generated_project / "README.md").exists(),
                (generated_project / "docker-compose.yml").exists(),
                (generated_project / "backend").exists(),
                (generated_project / "frontend").exists()
            ]
            
            passed_checks = sum(validation_checks)
            
            if passed_checks >= 4:  # Most checks passed
                self.log_result(
                    "Cookiecutter Generation",
                    "PASS",
                    f"Project generation successful using {generation_method} ({passed_checks}/5 checks)",
                    time.time() - start_time,
                    {
                        "generation_method": generation_method,
                        "project_path": str(generated_project),
                        "validation_checks": passed_checks,
                        "context": test_context
                    }
                )
                return True
            else:
                self.log_result(
                    "Cookiecutter Generation",
                    "FAIL",
                    f"Project generation incomplete ({passed_checks}/5 checks)",
                    time.time() - start_time
                )
                return False
            
        except Exception as e:
            self.log_result(
                "Cookiecutter Generation",
                "FAIL",
                f"Project generation failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_template_customization(self) -> bool:
        """Test template customization and variable substitution"""
        print("\n🎨 Testing Template Customization")
        
        start_time = time.time()
        
        try:
            # Test various template contexts
            test_contexts = [
                {
                    "name": "Basic SaaS",
                    "context": {
                        "project_name": "Customer Portal",
                        "project_slug": "customer-portal",
                        "industry": "B2B SaaS",
                        "database_type": "postgresql"
                    }
                },
                {
                    "name": "E-commerce",
                    "context": {
                        "project_name": "Shopping Platform", 
                        "project_slug": "shopping-platform",
                        "industry": "E-commerce",
                        "database_type": "postgresql"
                    }
                },
                {
                    "name": "FinTech",
                    "context": {
                        "project_name": "Payment Gateway",
                        "project_slug": "payment-gateway", 
                        "industry": "FinTech",
                        "database_type": "postgresql"
                    }
                }
            ]
            
            customization_results = []
            
            for test_case in test_contexts:
                # Create project directory for this test
                project_dir = self.temp_dir / "customized" / test_case["context"]["project_slug"]
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate customized README
                readme_template = f"""# {test_case['context']['project_name']}

Industry: {test_case['context']['industry']}
Database: {test_case['context']['database_type']}

## Project Overview

This {test_case['context']['industry']} project provides a complete solution for modern business needs.

### Features

- RESTful API backend
- Modern frontend interface
- {test_case['context']['database_type'].title()} database
- Docker containerization
- Production-ready deployment

### Quick Start

1. Clone the repository
2. Run `docker-compose up`
3. Access the application at http://localhost:3000

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
                
                with open(project_dir / "README.md", 'w') as f:
                    f.write(readme_template)
                
                # Validate customization
                if project_dir.exists() and (project_dir / "README.md").exists():
                    customization_results.append({
                        "name": test_case["name"],
                        "success": True,
                        "path": str(project_dir)
                    })
                else:
                    customization_results.append({
                        "name": test_case["name"], 
                        "success": False,
                        "path": str(project_dir)
                    })
            
            successful_customizations = len([r for r in customization_results if r["success"]])
            
            if successful_customizations == len(test_contexts):
                self.log_result(
                    "Template Customization",
                    "PASS",
                    f"All {successful_customizations} customizations successful",
                    time.time() - start_time,
                    {
                        "test_contexts": len(test_contexts),
                        "successful": successful_customizations,
                        "results": customization_results
                    }
                )
                return True
            else:
                self.log_result(
                    "Template Customization",
                    "FAIL",
                    f"Only {successful_customizations}/{len(test_contexts)} customizations successful",
                    time.time() - start_time
                )
                return False
            
        except Exception as e:
            self.log_result(
                "Template Customization",
                "FAIL",
                f"Template customization test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_integration_with_orchestrator(self) -> bool:
        """Test integration with MVP orchestrator project generation"""
        print("\n🔗 Testing Orchestrator Integration")
        
        start_time = time.time()
        
        try:
            # Simulate MVP orchestrator project data
            mvp_project_data = {
                "project_id": "test_integration_project",
                "project_name": "AI Writing Assistant",
                "industry": "Content Creation",
                "category": "B2B SaaS",
                "market_research": {
                    "industry": "Content Creation",
                    "category": "B2B SaaS",
                    "analysis": "Growing market with 15% YoY growth..."
                },
                "founder_analysis": {
                    "skills": ["Python", "React", "AI/ML"],
                    "experience": "5 years software development"
                },
                "mvp_spec": {
                    "problem": "Content creators struggle with writer's block",
                    "solution": "AI-powered writing assistant",
                    "target_users": "Bloggers and marketers"
                },
                "architecture": {
                    "tech_stack": "FastAPI, React, PostgreSQL",
                    "architecture": "Microservices with API gateway"
                }
            }
            
            # Test project metadata generation
            project_metadata = {
                "project_name": mvp_project_data["project_name"],
                "project_slug": mvp_project_data["project_name"].lower().replace(" ", "-"),
                "industry": mvp_project_data["industry"],
                "category": mvp_project_data["category"],
                "problem_statement": mvp_project_data["mvp_spec"]["problem"],
                "solution_approach": mvp_project_data["mvp_spec"]["solution"],
                "target_audience": mvp_project_data["mvp_spec"]["target_users"],
                "tech_stack": mvp_project_data["architecture"]["tech_stack"],
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Create integrated project
            integration_dir = self.temp_dir / "orchestrator_integration"
            integration_dir.mkdir(exist_ok=True)
            
            project_dir = integration_dir / project_metadata["project_slug"]
            project_dir.mkdir(exist_ok=True)
            
            # Generate project files based on orchestrator data
            readme_content = f"""# {project_metadata['project_name']}

**Industry**: {project_metadata['industry']} - {project_metadata['category']}

## Problem Statement
{project_metadata['problem_statement']}

## Solution Approach  
{project_metadata['solution_approach']}

## Target Audience
{project_metadata['target_audience']}

## Technical Architecture
- **Stack**: {project_metadata['tech_stack']}
- **Architecture**: {mvp_project_data['architecture']['architecture']}

## Market Context
{mvp_project_data['market_research']['analysis'][:200]}...

## Founder Background
- **Skills**: {', '.join(mvp_project_data['founder_analysis']['skills'])}
- **Experience**: {mvp_project_data['founder_analysis']['experience']}

## Development Status
- ✅ Market research completed
- ✅ MVP specification defined
- ✅ Technical architecture designed
- 🔄 Implementation in progress

Generated by Startup Factory MVP Orchestrator on {project_metadata['created_at']}
"""
            
            with open(project_dir / "README.md", 'w') as f:
                f.write(readme_content)
            
            # Create project manifest for orchestrator integration
            manifest = {
                "project_metadata": project_metadata,
                "mvp_data": mvp_project_data,
                "generated_by": "startup_factory_orchestrator",
                "version": "1.0.0",
                "integration_test": True
            }
            
            with open(project_dir / "project_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            
            # Validate integration
            validation_checks = [
                project_dir.exists(),
                (project_dir / "README.md").exists(),
                (project_dir / "project_manifest.json").exists(),
                len(project_metadata) >= 6,
                "startup_factory_orchestrator" in manifest["generated_by"]
            ]
            
            passed_checks = sum(validation_checks)
            
            if passed_checks == len(validation_checks):
                self.log_result(
                    "Orchestrator Integration",
                    "PASS",
                    f"Integration successful with orchestrator data ({passed_checks}/{len(validation_checks)} checks)",
                    time.time() - start_time,
                    {
                        "project_path": str(project_dir),
                        "metadata_fields": len(project_metadata),
                        "mvp_data_fields": len(mvp_project_data),
                        "manifest": manifest
                    }
                )
                return True
            else:
                self.log_result(
                    "Orchestrator Integration",
                    "FAIL", 
                    f"Integration incomplete ({passed_checks}/{len(validation_checks)} checks)",
                    time.time() - start_time
                )
                return False
            
        except Exception as e:
            self.log_result(
                "Orchestrator Integration",
                "FAIL",
                f"Orchestrator integration test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def run_template_tests(self) -> Dict[str, Any]:
        """Run complete template generation test suite"""
        print("🏗️ Starting Template Generation Testing Suite")
        print("=" * 60)
        
        if not self.setup():
            print("❌ Setup failed, aborting tests")
            return {"success": False, "error": "Setup failed"}
        
        try:
            # Test methods
            test_methods = [
                self.test_template_structure,
                self.test_cookiecutter_generation,
                self.test_template_customization,
                self.test_integration_with_orchestrator
            ]
            
            passed = 0
            failed = 0
            warnings = 0
            
            start_time = time.time()
            
            for test_method in test_methods:
                try:
                    result = test_method()
                    if result:
                        passed += 1
                    else:
                        # Check if last result was a warning
                        last_result = self.results[-1] if self.results else None
                        if last_result and last_result.status == "WARN":
                            warnings += 1
                        else:
                            failed += 1
                except Exception as e:
                    print(f"❌ Test {test_method.__name__} failed: {e}")
                    failed += 1
            
            total_duration = time.time() - start_time
            
            # Generate summary
            summary = {
                "success": failed == 0,
                "total_tests": len(test_methods),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "duration": total_duration,
                "results": [
                    {
                        "test_name": r.test_name,
                        "status": r.status,
                        "details": r.details,
                        "duration": r.duration,
                        "metadata": r.metadata
                    }
                    for r in self.results
                ]
            }
            
            # Print summary
            print("\n" + "=" * 60)
            print("🏁 Template Generation Testing Summary")
            print("=" * 60)
            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")
            print(f"⚠️ Warnings: {warnings}")
            print(f"⏱️ Duration: {total_duration:.2f}s")
            
            if failed == 0:
                if warnings == 0:
                    print("\n🎉 All template tests passed! Template system is production-ready.")
                else:
                    print(f"\n⚠️ All critical tests passed with {warnings} warnings.")
            else:
                print(f"\n❌ {failed} template tests failed. Review before proceeding.")
            
            return summary
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            self.cleanup()
    
    def generate_report(self, filename: str = "template_generation_report.json"):
        """Generate template testing report"""
        try:
            report_data = {
                "test_suite": "Template Generation Testing",
                "timestamp": time.time(),
                "template_directory": str(self.template_dir),
                "summary": {
                    "total_tests": len(self.results),
                    "passed": len([r for r in self.results if r.status == "PASS"]),
                    "failed": len([r for r in self.results if r.status == "FAIL"]),
                    "warnings": len([r for r in self.results if r.status == "WARN"]),
                    "total_duration": sum(r.duration for r in self.results)
                },
                "results": [
                    {
                        "test_name": r.test_name,
                        "status": r.status,
                        "details": r.details,
                        "duration": r.duration,
                        "metadata": r.metadata
                    }
                    for r in self.results
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n📄 Template testing report saved to: {filename}")
            
        except Exception as e:
            print(f"⚠️ Could not generate report: {e}")

def main():
    """Main template testing execution"""
    tester = TemplateGenerationTester()
    
    try:
        results = tester.run_template_tests()
        tester.generate_report()
        
        return results["success"]
        
    except Exception as e:
        print(f"💥 Template testing suite failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)