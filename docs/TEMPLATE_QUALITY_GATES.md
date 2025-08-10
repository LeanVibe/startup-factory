# Template Quality Gates System

Comprehensive validation framework for Startup Factory cookiecutter templates that ensures generated startup projects meet production quality standards.

## Overview

The Template Quality Gates system provides automated validation for cookiecutter templates used in the Startup Factory. It validates:

- **Structure**: Required files and directories
- **Configuration**: JSON/YAML/TOML file validity  
- **Code Quality**: Syntax, linting, and best practices
- **Functionality**: Build processes and test execution
- **Security**: Hardcoded secrets and vulnerability scanning
- **Performance**: Generation speed and resource usage

## Quick Start

### Validate All Templates
```bash
# Basic validation
make validate-templates

# CI/CD mode with strict quality gates
make validate-templates-ci
```

### Validate Specific Template
```bash
# Validate neoforge template
make validate-template TEMPLATE=neoforge

# Or use CLI directly
python tools/template_validator_cli.py validate --template neoforge --verbose
```

### Run Regression Tests
```bash
# Create baseline snapshots (first time)
python tools/template_validator_cli.py regression-test --create-baseline

# Run regression tests
make template-regression-test
```

## CLI Usage

The Template Validator CLI provides comprehensive template validation capabilities:

### Commands

#### List Templates
```bash
python tools/template_validator_cli.py list
```

#### Validate Single Template
```bash
python tools/template_validator_cli.py validate --template neoforge --verbose
```

#### Validate All Templates
```bash
# Default minimum score: 0.7
python tools/template_validator_cli.py validate-all

# Custom minimum score
python tools/template_validator_cli.py validate-all --min-score 0.8 --verbose
```

#### Regression Testing
```bash
# Create baseline snapshots (run once)
python tools/template_validator_cli.py regression-test --create-baseline

# Run regression tests
python tools/template_validator_cli.py regression-test --verbose
```

#### Performance Benchmarking
```bash
python tools/template_validator_cli.py benchmark --template neoforge --iterations 5
```

#### CI/CD Integration
```bash
# Runs full validation suite with strict quality gates
python tools/template_validator_cli.py ci --min-score 0.9
```

## Validation Categories

### 1. Structure Validation

Ensures generated projects contain all required files and directories.

**For neoforge template:**
- Essential files: `README.md`, `Makefile`, `docker-compose.yml`
- Backend files: `backend/requirements.txt`, `backend/app/main.py`, `backend/Dockerfile`
- Frontend files: `frontend/package.json`, `frontend/index.html`
- Directories: `backend`, `frontend`, `backend/app`, `backend/tests`, `frontend/src`, `docs`

### 2. Configuration Validation

Validates syntax and structure of configuration files:
- **JSON files**: Parse validation for `package.json`, `cookiecutter.json`, etc.
- **YAML files**: Parse validation for `docker-compose.yml`, `.github/workflows/`, etc.
- **TOML files**: Parse validation for `pyproject.toml`
- **INI files**: Parse validation for `pytest.ini`, `alembic.ini`, etc.

### 3. Code Quality Validation

Performs static analysis on generated code:

**Python Code:**
- Syntax validation using AST parsing
- Basic linting (line length, star imports)
- Import structure validation

**JavaScript/TypeScript Code:**
- Basic syntax checks
- Debug statement detection (`console.log`, `debugger`)
- Code quality patterns

### 4. Functionality Validation

Validates that generated projects can build and run:

**Backend Validation:**
- `requirements.txt` exists and is readable
- Python syntax validation for all `.py` files
- Basic dependency structure checks

**Frontend Validation:**
- `package.json` exists and contains required scripts
- Build script configuration validation
- Dependency structure validation

**Test Validation:**
- Test directory structure validation
- Test configuration file detection
- Basic test runner compatibility

### 5. Security Validation

Scans for security issues in generated templates:

**Hardcoded Secrets Detection:**
- API keys, secret keys, passwords, tokens
- Bearer tokens and authentication credentials
- Excludes test/example values

**Dangerous Code Patterns:**
- `eval()`, `exec()`, `__import__()` usage
- Unsafe subprocess calls
- System command execution

### 6. Performance Validation

Measures template generation performance:
- Generation time benchmarking
- Memory usage during generation
- Output size analysis
- Regression detection for performance

## Quality Scoring System

Each template receives a quality score from 0.0 to 1.0 based on:

| Category | Weight | Criteria |
|----------|---------|----------|
| Structure | 25% | Required files/directories present |
| Configuration | 20% | All config files parse successfully |
| Code Quality | 20% | Syntax valid, basic linting passes |
| Functionality | 20% | Build processes work, tests available |
| Security | 15% | No hardcoded secrets or dangerous patterns |

### Scoring Thresholds

- **0.9+**: Excellent - Production ready
- **0.8-0.89**: Good - Minor issues to address
- **0.7-0.79**: Acceptable - Some improvements needed
- **0.6-0.69**: Poor - Significant issues present
- **<0.6**: Critical - Major problems, not production ready

## Regression Testing

The regression testing system creates baseline snapshots and detects changes:

### Baseline Creation
```bash
python tools/template_validator_cli.py regression-test --create-baseline
```

Creates snapshots containing:
- Validation score
- File count and sizes
- File content hashes
- Validation details

### Regression Detection

Detects regressions when:
- Quality score decreases by >0.1
- Previously valid template becomes invalid
- Error count increases
- Critical files are deleted

### Snapshot Storage

Snapshots are stored in `template_snapshots/` directory:
- `{template_name}_baseline.json`: Baseline snapshot
- Includes metadata, hashes, and validation results

## CI/CD Integration

### GitHub Actions Integration

```yaml
name: Template Quality Gates
on: [push, pull_request]

jobs:
  template-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install cookiecutter
      - name: Validate templates
        run: make validate-templates-ci
      - name: Run regression tests
        run: make template-regression-test
```

### Quality Gate Enforcement

The CI mode enforces strict quality gates:
- **Minimum Score**: 0.8 (configurable)
- **All Templates Must Pass**: No template can fail validation
- **No Regressions**: Regression tests must pass
- **Performance Limits**: Generation time must be reasonable

## Error Types and Solutions

### Common Validation Errors

#### Structure Errors
```
Missing required file: backend/requirements.txt
Missing required directory: frontend/src
```
**Solution**: Ensure cookiecutter template includes all required files/directories.

#### Configuration Errors
```
Invalid JSON in package.json: Expecting ',' delimiter
Invalid YAML in docker-compose.yml: found undefined alias
```
**Solution**: Fix syntax errors in template configuration files.

#### Code Quality Errors
```
Python syntax error in app/main.py: invalid syntax
Line too long in models.py:45
```
**Solution**: Fix syntax and formatting issues in template code.

#### Security Warnings
```
Potential hardcoded secret in config.py: api_key = "sk-abc123..."
Dangerous code pattern in utils.py: eval(
```
**Solution**: Remove hardcoded secrets, use environment variables instead.

### Performance Issues

#### Slow Generation
```
Performance warning: Avg time (35.2s) exceeds warning threshold (30s)
```
**Solution**: Optimize template complexity, reduce file count, or simplify processing.

## Configuration

### Template Structure Requirements

Templates must follow this structure:
```
templates/
└── {template_name}/
    ├── cookiecutter.json          # Required
    ├── README.md                  # Optional but recommended
    └── {{cookiecutter.project_slug}}/
        ├── README.md              # Required in generated project
        ├── Makefile               # Required for neoforge
        ├── backend/               # Required for full-stack templates
        │   ├── requirements.txt   # Required
        │   ├── app/
        │   └── tests/
        └── frontend/              # Required for full-stack templates
            ├── package.json       # Required
            ├── src/
            └── test/
```

### Custom Validation Rules

You can customize validation rules by modifying `_get_required_structure()` in the validation framework:

```python
def _get_required_structure(self, template_name: str) -> Dict[str, List[str]]:
    structures = {
        "my_template": {
            "files": [
                "README.md",
                "pyproject.toml",
                "src/main.py"
            ],
            "directories": [
                "src",
                "tests",
                "docs"
            ]
        }
    }
    return structures.get(template_name, default_structure)
```

## Reports and Output

### Validation Reports

Generated reports include:
- Summary statistics (pass/fail counts, average scores)
- Individual template results
- Detailed error and warning messages
- Performance metrics
- Recommendations for improvements

### Report Formats

1. **Console Output**: Real-time validation progress and results
2. **Markdown Reports**: Detailed reports saved to files
3. **JSON Output**: Machine-readable results for CI/CD integration

### Example Report Output

```markdown
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
- Structure Score: 0.95
- Configuration Score: 0.90
- Code Quality Score: 0.85
- Functionality Score: 0.80
- Security Score: 0.85

### Warnings
- Line too long in backend/app/main.py:45
- No test script in frontend/package.json
```

## Best Practices

### Template Development

1. **Include All Required Files**: Ensure templates generate complete project structures
2. **Validate Configurations**: Test all JSON/YAML/TOML files are valid
3. **Follow Code Standards**: Use proper formatting and avoid dangerous patterns
4. **Provide Documentation**: Include comprehensive README and setup instructions
5. **Test Generation**: Regularly test template generation with various contexts

### Quality Gate Maintenance

1. **Regular Baseline Updates**: Update regression baselines when making intentional changes
2. **Monitor Performance**: Track template generation performance over time
3. **Security Scanning**: Regularly scan for new security patterns
4. **Threshold Tuning**: Adjust quality thresholds based on project requirements

### CI/CD Best Practices

1. **Fail Fast**: Run quality gates early in CI pipeline
2. **Parallel Execution**: Run template validation alongside other tests
3. **Caching**: Cache dependencies to speed up validation
4. **Reporting**: Generate reports for failed builds with actionable feedback

## Troubleshooting

### Common Issues

#### Dependencies Missing
```bash
pip install cookiecutter bandit pyyaml toml
```

#### Permission Errors
```bash
chmod +x tools/template_validator_cli.py
```

#### Template Not Found
```bash
# Check template exists
make list-templates

# Verify template structure
ls -la templates/neoforge/
```

### Debug Mode

Run with verbose output for detailed debugging:
```bash
python tools/template_validator_cli.py validate --template neoforge --verbose
```

### Performance Issues

If validation is slow:
1. Reduce iteration count for benchmarking
2. Check for large files in templates
3. Monitor system resources during validation

## Future Enhancements

### Planned Features

1. **Advanced Security Scanning**: Integration with Bandit, Safety, and Semgrep
2. **Dependency Vulnerability Scanning**: Check for known vulnerabilities in dependencies
3. **Template Linting**: Custom linting rules for template-specific patterns
4. **Performance Optimization**: Parallel validation and caching
5. **Custom Validators**: Plugin system for project-specific validation rules
6. **Integration Testing**: End-to-end testing of generated projects
7. **Visual Reports**: HTML dashboards with charts and graphs

### Contributing

To contribute to the Template Quality Gates system:

1. **Add New Validators**: Implement new validation checks in `test_template_quality_gates.py`
2. **Enhance CLI**: Add new commands or options to `template_validator_cli.py`
3. **Improve Performance**: Optimize validation algorithms and caching
4. **Add Tests**: Write tests for new validation features
5. **Update Documentation**: Keep this documentation current with changes

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run validation with `--verbose` flag for detailed output
3. Review generated reports for specific error messages
4. Check GitHub issues for known problems and solutions