
import sys
import os
import pathlib
import json

# Add current directory to path so we can import cli modules
sys.path.append(os.getcwd())

from cli.utils import shared
from cli.utils import constants

print("Debugging Stage File...")

try:
    # Try to fetch default stage
    stage = shared.fetch_stage_or_default(None, debug=True)
    print(f"Stage Path: {stage.stage_path}")
    
    # Read raw content
    with open(stage.stage_path, 'r') as f:
        content = json.load(f)
        print("Stage Content:")
        print(json.dumps(content, indent=2))
        
    print(f"Verified vpc_access_connector_id in object: {getattr(stage, 'vpc_access_connector_id', 'MISSING')}")
    
except Exception as e:
    print(f"Error fetching stage: {e}")
    # Search for any json files in cli/stages
    print("\nListing cli/stages content:")
    stages_dir = pathlib.Path("cli/stages")
    if stages_dir.exists():
        for p in stages_dir.iterdir():
            print(f" - {p}")
            if p.suffix == '.json':
                with open(p, 'r') as f:
                    print(f"   Content: {f.read()}")
    else:
        print("cli/stages directory not found")

