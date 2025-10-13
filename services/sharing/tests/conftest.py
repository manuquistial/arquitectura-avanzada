"""Pytest configuration for sharing service tests."""
import sys
from pathlib import Path

# Add service root to path
service_root = Path(__file__).parent.parent
sys.path.insert(0, str(service_root))

