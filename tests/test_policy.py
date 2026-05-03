"""
Tests: Policy composition.

Forwards all tests from test_policy_generation to maintain consistent
source-to-test module naming.
"""

import importlib
import sys

import tests
tests_dir = str(tests.__path__[0])
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

mod = importlib.import_module("test_policy_generation")
TestPolicyGeneration = mod.TestPolicyGeneration
