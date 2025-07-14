#!/usr/bin/env python3
"""
Test script for Meta-Fill tool
Simple validation that the tool works correctly
"""

import asyncio
import json
from pathlib import Path

async def test_meta_fill():
    """Test meta-fill functionality"""
    
    try:
        # Test 1: Import meta-fill modules
        print("🧪 Testing Meta-Fill imports...")
        import sys
        sys.path.append('.')
        
        # Import from the actual files (with hyphens replaced)
        import importlib.util
        
        # Load meta-fill.py
        spec = importlib.util.spec_from_file_location("meta_fill", "meta-fill.py")
        meta_fill = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(meta_fill)
        
        MetaFillApp = meta_fill.MetaFillApp
        ProjectMetadata = meta_fill.ProjectMetadata
        
        # Load meta-fill-integration.py  
        spec2 = importlib.util.spec_from_file_location("meta_fill_integration", "meta-fill-integration.py")
        meta_integration_module = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(meta_integration_module)
        
        MVPMetaIntegration = meta_integration_module.MVPMetaIntegration
        print("✅ Imports successful")
        
        # Test 2: Create sample metadata
        print("\n🧪 Testing metadata creation...")
        metadata = ProjectMetadata(
            project_name="Test AI Assistant",
            project_slug="test-ai-assistant",
            industry="Technology",
            category="B2B SaaS",
            description="A test AI assistant for validation",
            target_audience="Developers and tech teams"
        )
        print(f"✅ Metadata created: {metadata.project_name}")
        
        # Test 3: Convert to cookiecutter context
        print("\n🧪 Testing cookiecutter context conversion...")
        context = metadata.to_cookiecutter_context()
        print(f"✅ Context has {len(context)} fields")
        
        # Test 4: Save and load metadata
        print("\n🧪 Testing metadata persistence...")
        test_file = Path("test_metadata.json")
        with open(test_file, 'w') as f:
            json.dump(metadata.__dict__, f, indent=2, default=str)
        
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        
        loaded_metadata = ProjectMetadata(**loaded_data)
        print(f"✅ Metadata persistence works: {loaded_metadata.project_name}")
        
        # Cleanup
        test_file.unlink()
        
        # Test 5: Integration module
        print("\n🧪 Testing MVP integration...")
        integration = MVPMetaIntegration()
        print("✅ Integration module initialized")
        
        print("\n🎉 All tests passed! Meta-Fill tool is ready.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Run: uv run meta-fill.py --help")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_meta_fill())
    exit(0 if success else 1)