# Meta-Fill Tool for Startup Factory

AI-powered template and metadata generation for rapid MVP development

## Overview

The Meta-Fill tool is a comprehensive solution for generating project metadata and filling templates using AI. It's designed to integrate seamlessly with the Startup Factory MVP orchestrator workflow, enabling rapid project setup and configuration.

## Features

- **🤖 AI-Powered Metadata Generation**: Uses OpenAI and Anthropic to generate comprehensive project metadata
- **📝 Template Management**: Fills Cookiecutter templates with generated metadata
- **🔗 MVP Integration**: Seamlessly integrates with the MVP orchestrator workflow
- **📊 Project Structure**: Creates complete project structures with documentation
- **💰 Cost Tracking**: Tracks AI usage costs and provides budget management
- **🔍 Validation**: Multi-AI validation for metadata quality assurance

## Installation & Setup

### Prerequisites

- Python 3.10+
- uv package manager
- API keys for OpenAI and Anthropic

### Quick Start

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Configure API keys** in `config.yaml`:
   ```yaml
   openai_api_key: "your-openai-key"
   anthropic_api_key: "your-anthropic-key"
   ```

3. **Run the tool**:
   ```bash
   uv run meta-fill.py --help
   ```

## Usage

### Generate Project Metadata

Generate comprehensive project metadata from a business idea:

```bash
uv run meta-fill.py generate-meta \
  --industry "FinTech" \
  --category "B2B SaaS" \
  --idea "AI-powered expense tracking for small businesses" \
  --founder-background "5 years software development, 2 years fintech" \
  --output metadata.json
```

### Fill Project Template

Fill a project template using generated metadata:

```bash
uv run meta-fill.py fill-template \
  --template neoforge \
  --project-path ./my-project \
  --metadata-file metadata.json
```

### Update Existing Project

Update project metadata:

```bash
uv run meta-fill.py update-project \
  --project-id my-project \
  --data updated_data.json
```

### List Available Templates

```bash
uv run meta-fill.py list-templates
```

## Integration with MVP Orchestrator

The Meta-Fill tool is fully integrated with the MVP orchestrator workflow:

### Automatic Integration

When running the MVP orchestrator, Meta-Fill is automatically used in Phase 5 (Project Generation):

```bash
uv run mvp-orchestrator-script.py
# ... follow workflow through gates ...
# Phase 5 will automatically use Meta-Fill to generate complete project
```

### Manual Integration

Use the integration module directly:

```python
from meta_fill_integration import MVPMetaIntegration

integration = MVPMetaIntegration()

# Convert MVP data to project
metadata = await integration.generate_project_from_mvp_data(
    mvp_project_data, output_dir
)

# Create complete project
project_path = integration.create_startup_project(
    metadata, template_name="neoforge"
)
```

## Generated Project Structure

Meta-Fill creates comprehensive project structures:

```
my-project/
├── .startup-factory/           # Startup Factory specific files
│   ├── manifest.json          # Project manifest
│   └── workflow_checklist.md  # Development checklist
├── DEVELOPMENT_GUIDE.md       # Generated development guide
├── README.md                  # Project README
├── backend/                   # Backend code (from template)
├── frontend/                  # Frontend code (from template)
├── docs/                      # Documentation
└── enhanced_metadata.json     # Generated metadata
```

## Configuration

### Main Configuration (`config.yaml`)

```yaml
# AI Provider Settings
openai_api_key: "your-key"
anthropic_api_key: "your-key"

# AI Usage Preferences
use_openai_for_generation: true
use_anthropic_for_validation: true
max_tokens: 2000
temperature: 0.7

# Project Settings
default_template: "neoforge"
templates_directory: "../templates"
output_directory: "../projects"

# Quality Settings
enable_metadata_validation: true
enable_template_validation: true

# Cost Management
max_cost_per_generation: 0.50
warn_on_cost_threshold: 0.25
```

### Extended Configuration (`meta-fill-config.yaml`)

See `meta-fill-config.yaml` for detailed configuration options including:
- Business model defaults
- Technical defaults
- Validation rules
- Integration settings

## Project Metadata Schema

Generated metadata includes:

### Core Fields
- `project_name`: Human-readable project name
- `project_slug`: Machine-readable identifier
- `industry`: Business industry
- `category`: Business category
- `description`: Project description
- `target_audience`: Target user description

### Technical Fields
- `tech_stack`: Recommended technology stack
- `database_type`: Database choice
- `use_auth`: Authentication requirement
- `use_payments`: Payment integration
- `use_ai_features`: AI feature requirements

### Business Fields
- `business_model`: Revenue model
- `pricing_model`: Pricing strategy
- `target_market_size`: Market size estimate
- `competitive_advantage`: Unique value proposition

### Development Fields
- `estimated_development_time`: Timeline estimate
- `team_size`: Required team size
- `development_phase`: Current phase

## AI Integration Details

### Generation Process

1. **Initial Generation**: OpenAI GPT-4 generates comprehensive metadata
2. **Validation**: Anthropic Claude validates and refines metadata
3. **Enhancement**: Integration-specific enhancements applied
4. **Template Filling**: Cookiecutter processes filled with metadata

### Cost Management

- Tracks token usage and costs for each AI call
- Provides cost estimates before generation
- Implements cost limits and warnings
- Supports budget tracking across projects

### Quality Assurance

- Multi-AI validation for consistency
- Template variable validation
- Business logic validation
- Technical feasibility checks

## Templates

### Available Templates

- **neoforge**: Full-stack FastAPI + Lit PWA template
- Custom templates can be added to `../templates/` directory

### Template Requirements

Templates must be Cookiecutter-compatible with these variables:
- `project_name`
- `project_slug`
- `author_name`
- `author_email`
- `company_name`
- `license`
- Additional template-specific variables

## Error Handling

### Common Issues

1. **Missing API Keys**: Configure in `config.yaml`
2. **Template Not Found**: Check template name and directory
3. **Import Errors**: Ensure uv dependencies are installed
4. **Cost Limits**: Check budget settings in configuration

### Debugging

Enable debug mode:
```bash
DEBUG=1 uv run meta-fill.py generate-meta --industry "Tech" --category "SaaS" --idea "My idea"
```

View logs:
```bash
tail -f ~/.startup-factory/logs/meta-fill.log
```

## Integration Architecture

```
MVP Orchestrator
       ↓
   Meta-Fill Tool
       ↓
┌─────────────────┐    ┌──────────────────┐
│   AI Providers  │    │    Templates     │
│   - OpenAI      │    │   - neoforge     │
│   - Anthropic   │    │   - custom       │
└─────────────────┘    └──────────────────┘
       ↓                        ↓
┌─────────────────────────────────────────┐
│          Generated Project              │
│  - Complete codebase                    │
│  - Documentation                        │
│  - Configuration                        │
│  - Startup Factory integration          │
└─────────────────────────────────────────┘
```

## Performance

### Benchmarks

- Metadata generation: ~10-30 seconds
- Template filling: ~5-15 seconds
- Total project creation: ~30-60 seconds
- Memory usage: <100MB

### Optimization

- Parallel AI calls where possible
- Template caching
- Metadata reuse
- Cost-aware generation

## Contributing

### Adding New Templates

1. Create template in `../templates/new-template/`
2. Use Cookiecutter syntax for variables
3. Test with Meta-Fill tool
4. Document template variables

### Extending Metadata

1. Update `ProjectMetadata` class
2. Modify AI prompts
3. Update template variables
4. Test integration

### AI Provider Integration

1. Add provider to `AIConfig`
2. Implement provider methods
3. Update cost tracking
4. Test generation quality

## Examples

### Complete Workflow Example

```python
# Generate metadata
metadata = await app.generate_metadata_command(
    industry="FinTech",
    category="B2B SaaS", 
    project_idea="AI expense tracking",
    founder_background="Software developer with fintech experience"
)

# Fill template
project_path = app.fill_template_command(
    template_name="neoforge",
    project_path="./expense-tracker",
    metadata_file="metadata.json"
)

# Result: Complete project ready for development
```

### MVP Integration Example

```python
# Used automatically in MVP workflow
project_generation = await orchestrator.generate_complete_project(
    project_id="expense-tracker-mvp"
)
# Creates: Complete project with MVP orchestrator integration
```

## Troubleshooting

### Common Solutions

1. **Permission Errors**: Check file permissions and directory access
2. **Template Errors**: Validate template syntax and variables
3. **AI Errors**: Check API keys and rate limits
4. **Import Errors**: Reinstall dependencies with `uv`

### Support

- Check `META-FILL-README.md` for documentation
- Review `test-meta-fill.py` for examples
- Examine `meta-fill-config.yaml` for configuration
- Run `uv run meta-fill.py --help` for CLI help

## License

MIT License - See project root for details.

---

**Meta-Fill Tool v1.0** - Part of the Startup Factory ecosystem
Built for rapid MVP development with AI-powered automation.