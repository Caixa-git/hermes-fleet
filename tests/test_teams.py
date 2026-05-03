"""
Tests: Team preset loading.

Forwards all tests from test_team_presets to maintain consistent
source-to-test module naming.
"""

import importlib
import sys

# Ensure tests directory is in the import path
import tests
tests_dir = str(tests.__path__[0])
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# Delegate to the canonical test file
mod = importlib.import_module("test_team_presets")
TestTeamPresets = mod.TestTeamPresets
