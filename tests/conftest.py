"""Pytest configuration for test discovery and setup."""
import sys
import os

# Add src/ to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
