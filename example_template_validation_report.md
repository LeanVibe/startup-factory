# Template Quality Gates Report
Generated on: 2025-08-10 15:30:45

## Summary
- Total Templates: 2
- Passed: 2
- Failed: 0
- Average Score: 0.85

## neoforge ✅ PASS
- Score: 0.87
- Execution Time: 12.34s

### Structure Validation ✅
- Structure Score: 0.95
- Required Files: 8/8 found
- Required Directories: 6/6 found

**Found Files:**
- ✅ README.md
- ✅ Makefile  
- ✅ docker-compose.yml
- ✅ backend/requirements.txt
- ✅ backend/app/main.py
- ✅ backend/Dockerfile
- ✅ frontend/package.json
- ✅ frontend/index.html

**Found Directories:**
- ✅ backend
- ✅ frontend
- ✅ backend/app
- ✅ backend/tests
- ✅ frontend/src
- ✅ docs

### Configuration Validation ✅
- Configuration Score: 0.90
- JSON Files: 3 valid
- YAML Files: 4 valid
- TOML Files: 2 valid
- INI Files: 2 valid

**Configuration Files Validated:**
- ✅ cookiecutter.json
- ✅ frontend/package.json
- ✅ backend/pyproject.toml
- ✅ docker-compose.yml
- ✅ docker-compose.dev.yml
- ✅ docker-compose.prod.yml
- ✅ docker-compose.test.yml
- ✅ backend/pytest.ini
- ✅ backend/alembic.ini

### Code Quality Validation ⚠️
- Code Quality Score: 0.82
- Python Files: 45 checked
- JavaScript Files: 12 checked
- Syntax Errors: 0
- Lint Issues: 3

**Warnings:**
- ⚠️ Line too long in backend/app/core/config.py:67 (125 chars)
- ⚠️ Line too long in backend/app/models/user.py:23 (132 chars)
- ⚠️ Console.log found in frontend/src/components/debug.js

### Functionality Validation ✅
- Functionality Score: 0.85
- Backend Build: ✅ Passed
- Frontend Build: ✅ Passed
- Backend Tests: ✅ Configuration found
- Frontend Tests: ⚠️ No test script in package.json

**Build Results:**
- ✅ Backend: requirements.txt valid, 45 Python files syntax-checked
- ✅ Frontend: package.json valid, build script configured
- ✅ Backend Tests: pytest.ini configuration found
- ⚠️ Frontend Tests: No test script defined

### Security Validation ✅
- Security Score: 0.88
- Hardcoded Secrets: 0 found
- Dangerous Patterns: 0 found
- Security Issues: 1 warning

**Security Analysis:**
- ✅ No hardcoded API keys detected
- ✅ No dangerous eval() or exec() usage
- ✅ No system command injections
- ⚠️ Default admin credentials in backend/tests/conftest.py (test file - acceptable)

### Performance Metrics
- Template Generation Time: 12.34s
- Generated Project Size: 2.4 MB
- File Count: 127 files
- Memory Usage Peak: 45 MB

---

## reactnext ✅ PASS
- Score: 0.83
- Execution Time: 8.76s

### Structure Validation ✅
- Structure Score: 0.90
- Required Files: 4/4 found
- Required Directories: 2/2 found

**Found Files:**
- ✅ README.md
- ✅ package.json
- ✅ backend/requirements.txt
- ✅ frontend/next.config.js

**Found Directories:**
- ✅ backend
- ✅ frontend

### Configuration Validation ✅
- Configuration Score: 0.85
- JSON Files: 2 valid
- YAML Files: 1 valid
- JavaScript Config: 1 valid

**Configuration Files Validated:**
- ✅ cookiecutter.json
- ✅ package.json
- ✅ frontend/next.config.js
- ✅ docker-compose.yml

### Code Quality Validation ✅
- Code Quality Score: 0.88
- Python Files: 8 checked
- JavaScript Files: 15 checked
- Syntax Errors: 0
- Lint Issues: 1

**Warnings:**
- ⚠️ Line too long in backend/app.py:34 (128 chars)

### Functionality Validation ✅
- Functionality Score: 0.80
- Backend Build: ✅ Passed
- Frontend Build: ✅ Passed
- Tests: ⚠️ Minimal test configuration

**Build Results:**
- ✅ Backend: requirements.txt valid, 8 Python files syntax-checked
- ✅ Frontend: next.config.js valid, Next.js configuration proper
- ⚠️ Tests: Basic test structure but limited coverage

### Security Validation ✅
- Security Score: 0.85
- Hardcoded Secrets: 0 found
- Dangerous Patterns: 0 found

### Performance Metrics
- Template Generation Time: 8.76s
- Generated Project Size: 1.2 MB
- File Count: 67 files
- Memory Usage Peak: 28 MB

---

## Recommendations

### High Priority
1. **neoforge**: Add test script to frontend/package.json for complete test automation
2. **neoforge**: Fix line length issues in backend Python files
3. **reactnext**: Expand test coverage and configuration

### Medium Priority
1. **neoforge**: Remove console.log statement from frontend debug component
2. **reactnext**: Address line length warning in backend/app.py

### Low Priority
1. Consider adding more comprehensive linting rules for both templates
2. Add performance optimization guidelines to template documentation

## Quality Gate Status: ✅ PASSED

All templates meet minimum quality threshold (0.7). Average score of 0.85 indicates good template quality with minor improvements needed.

**Next Steps:**
1. Address high-priority recommendations
2. Update regression baselines after fixes
3. Schedule regular template validation in CI/CD pipeline

---

**Report Details:**
- Validation Framework Version: 1.0.0
- Templates Directory: /Users/bogdan/work/leanvibe-dev/startup-factory/templates
- Total Execution Time: 21.10s
- Generated Report Files: 
  - template_validation_report_20250810_153045.md
  - validation_results.json