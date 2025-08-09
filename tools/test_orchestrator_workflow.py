import asyncio
from pathlib import Path
import sys

# Ensure orchestrator script is importable
sys.path.append(str(Path(__file__).parent))

from mvp_orchestrator_script import example_usage

if __name__ == "__main__":
    asyncio.run(example_usage())
