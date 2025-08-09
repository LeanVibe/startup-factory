Below is a copy‑/‑paste run‑book you can follow on a brand‑new GitHub repository to bootstrap the entire Startup‑Factory workflow—including folder layout, boilerplate import, automation, and a GitHub Projects → Canvas board that tracks every initial task.

⸻

1 ▪ Prerequisites on your workstation

# Core tooling
brew install git gh cookiecutter direnv
asdf plugin add python nodejs
asdf install python 3.12.3
asdf install nodejs 20.11.0
pipx install pre-commit

# (Optional) GitHub CLI auth
gh auth login


⸻

2 ▪ Create and clone the empty repo

# 1. Create the repo on GitHub (private or public)
gh repo create startup-factory --private --confirm

# 2. Clone locally and enter it
git clone git@github.com:<your‑org>/startup-factory.git
cd startup-factory


⸻

3 ▪ Import the FastAPI + LitPWA boilerplate as a living template
1.Add a template branch that tracks the upstream starter:

git remote add starter https://github.com/neoforge-dev/starter.git
git fetch starter
git checkout -b template starter/main
git push -u origin template      # read‑only branch


startup2.StartupReturn to main and add the template mirror under templates/:

git checkout -b main
mkdir -p templates
git read-tree --prefix=templates/neoforge/ -u starter/main
git commit -m "chore: mirror neoforge starter into templates/"


sta3.starterRecord local overrides:

mkdir patches
echo "# Put .patch files here to customise boilerplate" > patches/README.md
git add patches/README.md
git commit -m "docs: add patches folder for boilerplate overrides"



This matches the living‑template strategy described in the handbook.  ￼

⸻

4 ▪ Lay out the monorepo skeleton

mkdir -p tools s-01/docs
touch tools/.gitkeep s-01/.gitkeep
git add .
git commit -m "chore: scaffold monorepo folders"

Feel free to create s‑02 … s‑10 now, or generate them later with the Make task in7.

⸻

5 ▪ Drop in the orchestrator & helper recipes

# Copy existing files from your local working dir or download
cp ~/path/to/mvp-orchestrator-script.py tools/mvp-orchestrator.py
mkdir tools/starter_ai_recipes
# add __init__.py + any recipe modules…

git add tools
git commit -m "feat(tools): add orchestrator and AI scaffold helpers"


⸻

6 ▪ Add baseline configuration & quality gates

# Editor & linting
curl -o .editorconfig https://raw.githubusercontent.com/neoforge-dev/starter/main/.editorconfig
echo '[tool.black]\nline-length = 88' > pyproject.toml
echo '[tool.ruff]\nline-length = 88'  >> pyproject.toml

# Pre‑commit
cat <<'EOF' > .pre‑commit‑config.yaml
repos:
  - repo: https://github.com/psf/black
      rev: 24.2.0
          hooks: [ { id: black  }  ]
            - repo: https://github.com/astral‑sh/ruff‑pre‑commit
                rev: v0.3.2
                    hooks: [ { id: ruff  }  ]
                    EOF
                    pre-commit install

                    git add .editorconfig pyproject.toml .pre‑commit‑config.yaml
                    git commit -m "chore(ci): formatting & lint config"


                    ⸻

                    7 ▪ Makefile utilities (optional but handy)

# Makefile (top‑level)
init:
\t@bash scripts/new_startup.sh $(STARTUP)

dev:
\t@docker compose up --build

ci:
\t@act -j lint-test

Create scripts/new_startup.sh that:

#!/usr/bin/env bash
set -e
dir=$1
cookiecutter templates/neoforge --output-dir=$dir --no-input

Commit both files.

⸻

8 ▪ GitHub Actions automation

.github/workflows/ci.yml

name: CI
on: [push, pull_request]
jobs:
  lint-test:
      runs-on: ubuntu-latest
          steps:
                - uses: actions/checkout@v4
                      - uses: actions/setup-python@v5
                              with: { python-version: '3.12'  }
                                    - run: pip install -r requirements-dev.txt
                                          - run: pre-commit run --all-files
                                                - run: pytest -q

                                                .github/workflows/orchestrator.yml

                                                name: Orchestrator
                                                on:
                                                  schedule: [ { cron: '*/5 * * * *'  }  ]
                                                    workflow_dispatch:
                                                    jobs:
                                                      run:
                                                          runs-on: ubuntu-latest
                                                              steps:
                                                                    - uses: actions/checkout@v4
                                                                          - uses: actions/setup-python@v5
                                                                                  with: { python-version: '3.12'  }
                                                                                        - run: pip install -r requirements.txt
                                                                                              - run: python tools/mvp-orchestrator.py

                                                                                              Push both:

                                                                                              git add .github
                                                                                              git commit -m "ci: add lint/test and orchestrator workflows"


                                                                                              ⸻

                                                                                              9 ▪ Set up the GitHub Projects → Canvas board
                                                                                              living1.lintingCreate a new Project

                                                                                              gh project create "Startup‑Factory Onboarding" --title "Startup‑Factory Onboarding"


                                                                                              LitPWA2.loginSwitch to Canvas view (GitHub UI → Projects β → Views → New → Canvas).
                                                                                              li3.lintAdd starter columns & cards

                                                                                              ColumnlivingCard (Drag lintingDetails
                                                                                              SetupLitPWARepo scaffolloginLink to commit chore: scaffold monorepo folders
                                                                                              liBoilerplate mirrorlintLink to commit adding templates/
                                                                                              AutomationlivingCI pipelintingIssue #1 automatically closed when CI passes
                                                                                              LitPWAOrchestrator cronloginIssue #2 track first successful run
                                                                                              DocsliStartup‑FactorylintAttach the markdown from previous answer
                                                                                              livingPrompt Library colintingCopy docs/prompt-library.md
                                                                                              First Startup (S‑01)LloginIssue template auto‑filed by orchestrator
                                                                                              Review GatesliG0 approvlintConvert to checkbox once humans review

                                                                                              living4.lintingEnable automatic issue cards
                                                                                              LitPWA•loginCanvas settings → Automation → “Automatically add issues with label ai-generated”.
                                                                                              with5.workflow_dispatchShare the project link with your new developer; they’ll see every task without needing private docs.

                                                                                              This replicates the gate & workflow map defined in the prompt library and PRD.

                                                                                              ⸻

                                                                                              10 ▪ Branch protection & worktree policy

                                                                                              gh api -X PUT repos/:owner/:repo/branches/main/protection \
                                                                                                -F required_status_checks.strict=true \
                                                                                                  -F required_status_checks.contexts='["lint-test"]' \
                                                                                                    -F enforce_admins=true \
                                                                                                      -F required_pull_request_reviews.dismiss_stale_reviews=true

                                                                                                      Add a repo‑level rule:

                                                                                                      Branch name pattern: feat/*
                                                                                                      Required PR reviewers: 1

                                                                                                      Each AI agent will therefore open a PR from its worktree branch (feat/backend/main-agent/###) that must pass CI before merge.

                                                                                                      ⸻

                                                                                                      11 ▪ Seed the first startup (S‑01)

# Create a blank issue that kicks off the orchestrator
gh issue create -t "Init S‑01" -l bootstrap -b "Please generate research docs"

Wait for the workflow to run; the orchestrator will:
with1.workflow_dispatchSpawn Perplexity to build the Market Opportunity Analysis doc.
2.Commit it to s‑01/docs/ on branch research/s‑01.
3.Open a draft PR and create a Canvas card (auto‑labelled ai-generated).

⸻

12 ▪ Next steps for the onboarded dev
•Pull the repo, open the Canvas board, and pick the Setup → Repo scaffold card if any unchecked items remain.
•Use git worktree add ../wt‑backend-dev feat/backend/human/001 to claim a task.
•Open a PR, pass CI, and drag the card to Done.

⸻

Your empty repo is now a factory conveyor belt—boilerplate, docs, gates, automation, and visual Canvas board all wired in and ready for ten parallel MVPs. Happy building!
