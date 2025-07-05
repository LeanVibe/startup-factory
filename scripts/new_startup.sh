#!/usr/bin/env bash
set -e
dir=$1
cookiecutter templates/neoforge --output-dir=$dir --no-input
