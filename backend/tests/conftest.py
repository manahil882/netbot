import os
import sys

# Add the backend directory to sys.path so tests can import the 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
