import os
from pathlib import Path

# Automatically load environment variables from apps/api/.env for the test run
env_file = Path(__file__).resolve().parents[1] / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip("'\"")
                # Set the variable if not already set in the parent environment
                os.environ.setdefault(key.strip(), val)
