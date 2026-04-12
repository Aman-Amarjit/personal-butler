"""
JARVIS AI Assistant - Launcher

Run from the project root:
    python run.py
    python run.py --debug
    python run.py --no-voice
    python run.py --monitor 1
"""

import sys
import os

# Make sure src/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
