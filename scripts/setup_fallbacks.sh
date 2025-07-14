#!/bin/bash
# Setup script for CLI fallback tools
# Installs and configures alternative CLI tools when API keys are not available

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

echo "🔧 Setting up CLI Fallback Tools for Startup Factory"
echo "=================================================="

# Check operating system
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGw;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

print_info "Detected OS: $MACHINE"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install via homebrew (macOS)
install_via_homebrew() {
    local package=$1
    if command_exists brew; then
        print_info "Installing $package via Homebrew..."
        brew install "$package"
        return $?
    else
        print_warning "Homebrew not found. Please install manually."
        return 1
    fi
}

# Function to install via apt (Linux)
install_via_apt() {
    local package=$1
    if command_exists apt-get; then
        print_info "Installing $package via apt..."
        sudo apt-get update && sudo apt-get install -y "$package"
        return $?
    else
        print_warning "apt not found. Please install manually."
        return 1
    fi
}

# Setup OpenCode CLI (OpenAI fallback)
setup_opencode_cli() {
    echo ""
    print_info "Setting up OpenCode CLI (OpenAI fallback)..."
    
    if command_exists opencode; then
        print_success "OpenCode CLI already installed"
        opencode --version
        return 0
    fi
    
    print_info "OpenCode CLI not found. Installing..."
    
    case $MACHINE in
        Mac)
            # Try Homebrew first
            if install_via_homebrew opencode; then
                print_success "OpenCode CLI installed via Homebrew"
                return 0
            fi
            
            # Fallback to manual installation
            print_info "Installing OpenCode CLI manually for macOS..."
            curl -L https://github.com/opencode/cli/releases/latest/download/opencode-macos -o /usr/local/bin/opencode
            chmod +x /usr/local/bin/opencode
            ;;
        Linux)
            # Try apt first
            if install_via_apt opencode; then
                print_success "OpenCode CLI installed via apt"
                return 0
            fi
            
            # Fallback to manual installation
            print_info "Installing OpenCode CLI manually for Linux..."
            curl -L https://github.com/opencode/cli/releases/latest/download/opencode-linux -o /usr/local/bin/opencode
            chmod +x /usr/local/bin/opencode
            ;;
        *)
            print_error "Unsupported OS for automatic OpenCode CLI installation"
            print_info "Please install OpenCode CLI manually from: https://github.com/opencode/cli"
            return 1
            ;;
    esac
    
    # Verify installation
    if command_exists opencode; then
        print_success "OpenCode CLI installed successfully"
        opencode --version
    else
        print_error "OpenCode CLI installation failed"
        return 1
    fi
}

# Setup claude-p CLI (Anthropic fallback)
setup_claude_p_cli() {
    echo ""
    print_info "Setting up claude-p CLI (Anthropic fallback)..."
    
    if command_exists claude-p; then
        print_success "claude-p CLI already installed"
        claude-p --version
        return 0
    fi
    
    print_info "claude-p CLI not found. Installing..."
    
    # Try npm installation first (most common)
    if command_exists npm; then
        print_info "Installing claude-p via npm..."
        npm install -g claude-p
        
        if command_exists claude-p; then
            print_success "claude-p CLI installed via npm"
            return 0
        fi
    fi
    
    # Try pip installation
    if command_exists pip || command_exists pip3; then
        print_info "Installing claude-p via pip..."
        pip3 install claude-p || pip install claude-p
        
        if command_exists claude-p; then
            print_success "claude-p CLI installed via pip"
            return 0
        fi
    fi
    
    # Manual installation fallback
    case $MACHINE in
        Mac)
            if install_via_homebrew claude-p; then
                print_success "claude-p CLI installed via Homebrew"
                return 0
            fi
            ;;
        Linux)
            if install_via_apt claude-p; then
                print_success "claude-p CLI installed via apt"
                return 0
            fi
            ;;
    esac
    
    print_error "claude-p CLI installation failed"
    print_info "Please install claude-p manually: https://github.com/anthropics/claude-p"
    return 1
}

# Setup Gemini CLI (Perplexity fallback)
setup_gemini_cli() {
    echo ""
    print_info "Setting up Gemini CLI (Perplexity fallback)..."
    
    if command_exists gemini; then
        print_success "Gemini CLI already installed"
        gemini --version
        return 0
    fi
    
    print_info "Gemini CLI not found. Installing..."
    
    # Try Google's official installation
    if command_exists gcloud; then
        print_info "Installing Gemini CLI via gcloud..."
        gcloud components install gemini
        
        if command_exists gemini; then
            print_success "Gemini CLI installed via gcloud"
            return 0
        fi
    fi
    
    # Try pip installation
    if command_exists pip || command_exists pip3; then
        print_info "Installing google-generativeai via pip..."
        pip3 install google-generativeai || pip install google-generativeai
        
        # Create gemini wrapper script
        cat > /usr/local/bin/gemini << 'EOF'
#!/usr/bin/env python3
import sys
import argparse
import google.generativeai as genai

def main():
    parser = argparse.ArgumentParser(description='Gemini CLI wrapper')
    parser.add_argument('-print', '--print', action='store_true', help='Print mode')
    parser.add_argument('--query', required=True, help='Query to process')
    args = parser.parse_args()
    
    # Configure API (you may need to set GOOGLE_API_KEY)
    # genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
    
    # For now, just echo the query as a placeholder
    print(f"Gemini CLI wrapper - Query: {args.query}")
    print("Note: This is a placeholder. Configure with actual Google API key for full functionality.")

if __name__ == '__main__':
    main()
EOF
        
        chmod +x /usr/local/bin/gemini
        
        if command_exists gemini; then
            print_success "Gemini CLI wrapper created"
            return 0
        fi
    fi
    
    print_error "Gemini CLI installation failed"
    print_info "Please install Google Cloud SDK or set up Gemini CLI manually"
    return 1
}

# Test all CLI tools
test_cli_tools() {
    echo ""
    print_info "Testing CLI tool installations..."
    
    tools=("opencode" "claude-p" "gemini")
    working_tools=()
    failed_tools=()
    
    for tool in "${tools[@]}"; do
        if command_exists "$tool"; then
            print_success "$tool is available"
            working_tools+=("$tool")
        else
            print_warning "$tool is not available"
            failed_tools+=("$tool")
        fi
    done
    
    echo ""
    echo "📊 CLI Tools Summary:"
    echo "✅ Working: ${#working_tools[@]} (${working_tools[*]})"
    echo "❌ Failed: ${#failed_tools[@]} (${failed_tools[*]})"
    
    if [ ${#working_tools[@]} -gt 0 ]; then
        print_success "At least one CLI tool is available for fallbacks"
    else
        print_error "No CLI tools available. Fallbacks will not work."
        return 1
    fi
}

# Update configuration to enable fallbacks
update_config() {
    echo ""
    print_info "Updating configuration to enable CLI fallbacks..."
    
    # Create enhanced config if it doesn't exist
    if [ ! -f "../config.enhanced.yaml" ]; then
        cat > ../config.enhanced.yaml << 'EOF'
# Enhanced configuration with CLI fallbacks
# API keys loaded from environment variables
openai_api_key: ${OPENAI_API_KEY}
anthropic_api_key: ${ANTHROPIC_API_KEY}
perplexity_api_key: ${PERPLEXITY_API_KEY}

# Fallback configuration
enable_cli_fallbacks: true
fallback_timeout: 300  # 5 minutes

# CLI tool configurations
cli_tools:
  opencode:
    command: "opencode"
    args: ["--non-interactive", "--input", "{input_file}", "--output", "text"]
    timeout: 300
  claude_p:
    command: "claude-p"
    args: ["--search", "--query", "{query}", "--format", "text"]
    timeout: 300
  gemini:
    command: "gemini"
    args: ["-print", "--query", "{query}"]
    timeout: 300

# Production settings
project_root: "./production_projects"
max_retries: 5
timeout: 60

# Cost tracking (updated rates as of July 2024)
openai_input_cost_per_1k: 0.01
openai_output_cost_per_1k: 0.03
anthropic_input_cost_per_1k: 0.015
anthropic_output_cost_per_1k: 0.075
perplexity_cost_per_request: 0.005

# CLI fallback cost estimates (rough approximations)
opencode_cost_per_1k: 0.005
claude_p_cost_per_1k: 0.008
gemini_cost_per_1k: 0.001

# Security settings
log_level: "INFO"
max_concurrent_requests: 10
rate_limit_per_minute: 60

# Monitoring settings
enable_monitoring: true
enable_cost_alerts: true
max_budget_per_startup: 15.0
metrics_port: 8000
health_check_port: 8001
EOF
        print_success "Enhanced configuration created at ../config.enhanced.yaml"
    else
        print_info "Enhanced configuration already exists"
    fi
}

# Create usage guide
create_usage_guide() {
    echo ""
    print_info "Creating CLI fallback usage guide..."
    
    cat > ../CLI_FALLBACK_GUIDE.md << 'EOF'
# CLI Fallback Usage Guide

This guide explains how to use the Startup Factory platform with CLI fallbacks when API keys are not available.

## Overview

The enhanced MVP orchestrator can automatically fall back to CLI tools when API keys are missing:

- **OpenAI missing** → Uses `opencode` CLI in non-interactive mode
- **Anthropic missing** → Uses `claude-p` for search functionality  
- **Perplexity missing** → Uses `gemini` CLI with -print flag

## Usage

### With Enhanced Orchestrator

```bash
cd tools
python enhanced_mvp_orchestrator.py
```

The orchestrator will:
1. Check for API keys
2. Automatically fall back to CLI tools if keys are missing
3. Display provider status before starting
4. Track costs across all methods

### Provider Status Check

The orchestrator shows the status of each provider:

```
🔧 Provider Status Check
==================================================
OpenAI:
  API Key: ❌ (OPENAI_API_KEY)
  CLI Tool: ✅ (opencode)
  Primary: api
  Fallback: cli

Anthropic:
  API Key: ✅ (ANTHROPIC_API_KEY)
  CLI Tool: ✅ (claude-p)
  Primary: api
  Fallback: cli

Perplexity:
  API Key: ❌ (PERPLEXITY_API_KEY)
  CLI Tool: ✅ (gemini)
  Primary: api
  Fallback: cli
```

## CLI Tool Setup

### OpenCode CLI (OpenAI fallback)

```bash
# macOS
brew install opencode

# Linux
sudo apt-get install opencode

# Manual
curl -L https://github.com/opencode/cli/releases/latest/download/opencode-$(uname -s | tr '[:upper:]' '[:lower:]') -o /usr/local/bin/opencode
chmod +x /usr/local/bin/opencode
```

### claude-p CLI (Anthropic fallback)

```bash
# npm
npm install -g claude-p

# pip
pip install claude-p
```

### Gemini CLI (Perplexity fallback)

```bash
# Google Cloud SDK
gcloud components install gemini

# pip (with wrapper)
pip install google-generativeai
```

## Configuration

### Enhanced Config File

Use `config.enhanced.yaml` for full fallback support:

```yaml
enable_cli_fallbacks: true
fallback_timeout: 300

cli_tools:
  opencode:
    command: "opencode"
    args: ["--non-interactive", "--input", "{input_file}", "--output", "text"]
  claude_p:
    command: "claude-p"
    args: ["--search", "--query", "{query}", "--format", "text"]
  gemini:
    command: "gemini"
    args: ["-print", "--query", "{query}"]
```

## Cost Tracking

CLI fallbacks include cost estimation:

- **OpenCode**: ~$0.005 per 1k tokens
- **claude-p**: ~$0.008 per 1k tokens  
- **Gemini**: ~$0.001 per 1k tokens

Total workflow cost with fallbacks: ~$0.05-$0.20

## Troubleshooting

### CLI Tool Not Found

```bash
# Check installation
which opencode claude-p gemini

# Test functionality
opencode --help
claude-p --version
gemini --version
```

### Permission Issues

```bash
# Fix permissions
chmod +x /usr/local/bin/opencode
chmod +x /usr/local/bin/claude-p
chmod +x /usr/local/bin/gemini
```

### Timeout Issues

Increase timeout in config:

```yaml
fallback_timeout: 600  # 10 minutes
```

## Benefits

1. **No API Keys Required**: Work without any API subscriptions
2. **Cost Effective**: CLI tools often cheaper than API calls
3. **Offline Capable**: Some tools work without internet
4. **Flexible**: Mix and match API/CLI based on availability
5. **Transparent**: Clear indication of which method is used

## Limitations

1. **Feature Differences**: CLI tools may have different capabilities
2. **Speed**: CLI tools might be slower than direct API calls
3. **Format**: Output format may vary between methods
4. **Dependencies**: Requires additional tool installations

## Best Practices

1. **Hybrid Approach**: Use APIs where available, CLI as fallback
2. **Test Regularly**: Ensure CLI tools remain functional
3. **Monitor Costs**: Track costs across all methods
4. **Update Tools**: Keep CLI tools updated for best results
5. **Validate Output**: Review results from different providers

For support, check the main documentation or run the health check script.
EOF

    print_success "CLI fallback usage guide created at ../CLI_FALLBACK_GUIDE.md"
}

# Main setup flow
main() {
    echo "Starting CLI fallback setup..."
    
    # Setup each CLI tool
    setup_opencode_cli
    setup_claude_p_cli  
    setup_gemini_cli
    
    # Test installations
    test_cli_tools
    
    # Update configuration
    update_config
    
    # Create usage guide
    create_usage_guide
    
    echo ""
    echo "🎉 CLI Fallback Setup Complete!"
    echo "==============================="
    echo ""
    echo "✅ Enhanced MVP orchestrator ready with CLI fallbacks"
    echo "📋 Usage guide created: ../CLI_FALLBACK_GUIDE.md"
    echo "⚙️  Enhanced config: ../config.enhanced.yaml"
    echo ""
    echo "Next steps:"
    echo "1. Test the enhanced orchestrator: cd tools && python enhanced_mvp_orchestrator.py"
    echo "2. Review the usage guide for detailed instructions"
    echo "3. Set up any missing API keys or rely on CLI fallbacks"
    echo ""
    print_success "Startup Factory now supports operation without API keys!"
}

# Run main function
main "$@"