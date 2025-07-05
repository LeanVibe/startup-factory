#!/usr/bin/env bash
set -e
startup_name=$1
if [ -z "$startup_name" ]; then
    echo "Usage: $0 <startup_name>"
    exit 1
fi

# Simple copy approach for now - we'll enhance with cookiecutter later
echo "Creating startup: $startup_name"
cp -r templates/neoforge/{{cookiecutter.project_slug}} "$startup_name"
echo "Startup '$startup_name' created successfully!"
echo "Next steps:"
echo "  cd $startup_name"
echo "  make dev"
