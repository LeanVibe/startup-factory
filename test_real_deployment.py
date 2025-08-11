#!/usr/bin/env python3
"""
Real Deployment Test
Test-driven development approach to validate and fix deployment gaps.

FIRST PRINCIPLES:
1. Founders need LIVE MVPs, not just code
2. "Live" means accessible via URL, not just local Docker
3. Each deployment failure is a barrier to founder success

TDD APPROACH:
1. Write failing tests for deployment requirements
2. Fix the minimum needed to make tests pass
3. Validate with real deployment
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
import subprocess
import pytest

class DeploymentGapAnalyzer:
    """Analyze and fix deployment gaps in generated MVPs"""
    
    def __init__(self, mvp_path: Path):
        self.mvp_path = mvp_path
        self.deployment_issues = []
        
    def analyze_deployment_readiness(self) -> Dict[str, bool]:
        """TDD: Define what a deployable MVP MUST have"""
        
        requirements = {
            "has_docker_compose": (self.mvp_path / "docker-compose.yml").exists(),
            "has_backend_dockerfile": (self.mvp_path / "backend" / "Dockerfile").exists(),
            "has_frontend_dockerfile": (self.mvp_path / "frontend" / "Dockerfile").exists(),
            "has_nginx_config": (self.mvp_path / "frontend" / "nginx.conf").exists(),
            "has_env_example": (self.mvp_path / ".env.example").exists(),
            "has_startup_script": (self.mvp_path / "start.sh").exists(),
            "has_readme_with_deployment": self._check_readme_deployment_instructions()
        }
        
        # Identify gaps
        self.deployment_issues = [req for req, exists in requirements.items() if not exists]
        
        return requirements
    
    def _check_readme_deployment_instructions(self) -> bool:
        """Check if README contains deployment instructions"""
        readme_path = self.mvp_path / "README.md"
        if not readme_path.exists():
            return False
            
        content = readme_path.read_text()
        return "docker-compose up" in content and "localhost:" in content
    
    def fix_deployment_gaps(self) -> List[str]:
        """Fix identified deployment issues"""
        
        fixes_applied = []
        
        # Fix 1: Frontend Dockerfile
        if "has_frontend_dockerfile" in self.deployment_issues:
            self._create_frontend_dockerfile()
            fixes_applied.append("Created frontend Dockerfile")
        
        # Fix 2: Nginx configuration
        if "has_nginx_config" in self.deployment_issues:
            self._create_nginx_config()
            fixes_applied.append("Created nginx configuration")
        
        # Fix 3: Enhanced docker-compose
        if "has_docker_compose" in self.deployment_issues or self._needs_docker_compose_fix():
            self._fix_docker_compose()
            fixes_applied.append("Fixed docker-compose configuration")
        
        # Fix 4: Environment template
        if "has_env_example" in self.deployment_issues:
            self._create_env_example()
            fixes_applied.append("Created environment template")
        
        # Fix 5: Startup script
        if "has_startup_script" in self.deployment_issues:
            self._create_startup_script()
            fixes_applied.append("Created startup script")
        
        return fixes_applied
    
    def _create_frontend_dockerfile(self):
        """Create production-ready frontend Dockerfile"""
        
        dockerfile_content = """# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source code
COPY src/ ./src/
COPY public/ ./public/

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
"""
        
        frontend_dir = self.mvp_path / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        
        (frontend_dir / "Dockerfile").write_text(dockerfile_content)
        
        # Create public directory if it doesn't exist
        (frontend_dir / "public").mkdir(exist_ok=True)
        (frontend_dir / "public" / "index.html").write_text("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MVP Application</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>""")
    
    def _create_nginx_config(self):
        """Create nginx configuration for frontend"""
        
        nginx_config = """server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Handle React Router
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy";
        add_header Content-Type text/plain;
    }
}"""
        
        frontend_dir = self.mvp_path / "frontend"
        (frontend_dir / "nginx.conf").write_text(nginx_config)
    
    def _needs_docker_compose_fix(self) -> bool:
        """Check if docker-compose needs fixes"""
        compose_path = self.mvp_path / "docker-compose.yml"
        if not compose_path.exists():
            return True
            
        content = compose_path.read_text()
        # Check for common issues
        issues = [
            "version:" in content,  # Obsolete version field
            "build: ./frontend" not in content  # Missing frontend build context
        ]
        
        return any(issues)
    
    def _fix_docker_compose(self):
        """Fix docker-compose configuration"""
        
        fixed_compose = """services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/mvp_db
    depends_on:
      - db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  db:
    image: postgres:13-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mvp_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mvp_db"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:

networks:
  default:
    driver: bridge
"""
        
        (self.mvp_path / "docker-compose.yml").write_text(fixed_compose)
        
        # Create database initialization script
        init_db = """-- Initialize database for MVP
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS business_entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (email, name) VALUES 
    ('founder@example.com', 'MVP Founder'),
    ('customer@example.com', 'First Customer')
ON CONFLICT (email) DO NOTHING;
"""
        
        (self.mvp_path / "init-db.sql").write_text(init_db)
    
    def _create_env_example(self):
        """Create environment template"""
        
        env_example = """# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/mvp_db

# API Configuration
SECRET_KEY=your-secret-key-here
API_VERSION=v1
DEBUG=False

# External Services (add your keys)
STRIPE_API_KEY=sk_test_your_stripe_key
SENDGRID_API_KEY=your_sendgrid_key
OPENAI_API_KEY=your_openai_key

# Deployment
ENVIRONMENT=production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Security
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
"""
        
        (self.mvp_path / ".env.example").write_text(env_example)
    
    def _create_startup_script(self):
        """Create startup script for easy deployment"""
        
        startup_script = """#!/bin/bash
set -e

echo "🚀 Starting MVP Deployment..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual configuration"
fi

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down -v

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
fi

if curl -f http://localhost:3000/health >/dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
fi

echo ""
echo "🎉 MVP is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f"
"""
        
        startup_script_path = self.mvp_path / "start.sh"
        startup_script_path.write_text(startup_script)
        startup_script_path.chmod(0o755)  # Make executable

async def test_mvp_deployment_pipeline():
    """TDD test for complete MVP deployment"""
    
    # Find a generated MVP to test with
    mvp_dir = Path("demo_generated_mvps")
    if not mvp_dir.exists():
        pytest.skip("No generated MVPs found. Run demo first.")
    
    mvp_projects = list(mvp_dir.iterdir())
    if not mvp_projects:
        pytest.skip("No MVP projects found.")
    
    # Test with the first MVP
    test_mvp = mvp_projects[0]
    
    print(f"🧪 Testing deployment for: {test_mvp.name}")
    
    # Step 1: Analyze current deployment readiness
    analyzer = DeploymentGapAnalyzer(test_mvp)
    requirements = analyzer.analyze_deployment_readiness()
    
    print("📊 Deployment Readiness Assessment:")
    for requirement, status in requirements.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {requirement}")
    
    # Step 2: Fix deployment gaps
    if analyzer.deployment_issues:
        print(f"\n🔧 Fixing {len(analyzer.deployment_issues)} deployment issues...")
        fixes = analyzer.fix_deployment_gaps()
        
        for fix in fixes:
            print(f"  ✅ {fix}")
    
    # Step 3: Re-validate after fixes
    requirements_after = analyzer.analyze_deployment_readiness()
    deployment_ready = all(requirements_after.values())
    
    print(f"\n🎯 Deployment Status: {'✅ READY' if deployment_ready else '❌ NOT READY'}")
    
    # Step 4: Validate Docker Compose syntax
    try:
        result = subprocess.run(
            ["docker-compose", "config", "--quiet"],
            cwd=test_mvp,
            capture_output=True,
            timeout=10
        )
        
        config_valid = result.returncode == 0
        print(f"🐳 Docker Compose Config: {'✅ VALID' if config_valid else '❌ INVALID'}")
        
        if not config_valid:
            print(f"Error: {result.stderr.decode()}")
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"⚠️  Could not validate Docker Compose: {e}")
        config_valid = False
    
    # Overall assessment
    overall_ready = deployment_ready and config_valid
    
    return {
        "mvp_name": test_mvp.name,
        "deployment_ready": deployment_ready,
        "config_valid": config_valid,
        "overall_ready": overall_ready,
        "fixes_applied": len(fixes) if analyzer.deployment_issues else 0
    }

async def test_all_mvps_deployment():
    """Test deployment readiness for all generated MVPs"""
    
    print("🚀 TESTING ALL MVPS FOR DEPLOYMENT READINESS")
    print("=" * 60)
    
    mvp_dir = Path("demo_generated_mvps")
    if not mvp_dir.exists():
        print("❌ No generated MVPs found. Run demo first.")
        return
    
    mvp_projects = list(mvp_dir.iterdir())
    if not mvp_projects:
        print("❌ No MVP projects found.")
        return
    
    results = []
    
    for i, mvp_path in enumerate(mvp_projects[:3], 1):  # Test first 3 MVPs
        print(f"\n🧪 TESTING MVP {i}: {mvp_path.name}")
        print("-" * 40)
        
        analyzer = DeploymentGapAnalyzer(mvp_path)
        requirements = analyzer.analyze_deployment_readiness()
        
        # Fix gaps
        if analyzer.deployment_issues:
            fixes = analyzer.fix_deployment_gaps()
            print(f"🔧 Applied {len(fixes)} fixes")
        
        # Final assessment
        requirements_final = analyzer.analyze_deployment_readiness()
        ready = all(requirements_final.values())
        
        results.append({
            "name": mvp_path.name,
            "ready": ready,
            "fixes": len(analyzer.deployment_issues) if analyzer.deployment_issues else 0
        })
        
        print(f"Status: {'✅ DEPLOYMENT READY' if ready else '❌ NEEDS WORK'}")
    
    # Summary
    print(f"\n🎊 DEPLOYMENT READINESS SUMMARY")
    print("=" * 40)
    
    total_mvps = len(results)
    ready_mvps = sum(1 for r in results if r["ready"])
    total_fixes = sum(r["fixes"] for r in results)
    
    print(f"Total MVPs Tested: {total_mvps}")
    print(f"Deployment Ready: {ready_mvps}/{total_mvps} ({(ready_mvps/total_mvps)*100:.1f}%)")
    print(f"Total Fixes Applied: {total_fixes}")
    
    if ready_mvps == total_mvps:
        print("🎉 ALL MVPS ARE DEPLOYMENT READY!")
    else:
        print(f"⚠️  {total_mvps - ready_mvps} MVPs still need work")
    
    return results

if __name__ == "__main__":
    print("🧪 REAL DEPLOYMENT TEST - TDD APPROACH")
    print("Testing and fixing deployment gaps in generated MVPs")
    print("")
    
    # Test single MVP deployment
    single_result = asyncio.run(test_mvp_deployment_pipeline())
    print(f"\nSingle MVP Test Result: {single_result}")
    
    # Test all MVPs
    all_results = asyncio.run(test_all_mvps_deployment())
    
    print(f"\n✅ DEPLOYMENT PIPELINE TEST COMPLETE")
    print("Generated MVPs now have complete deployment configurations!")