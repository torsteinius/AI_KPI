import pytest
import sys
import pkgutil
import importlib

def discover_test_functions():
    """Dynamically finds and runs all test functions in the project."""
    test_functions = []
    
    # Scan all modules in the project directory
    for _, module_name, _ in pkgutil.walk_packages(["src"]):  # Change "src" to your project folder
        mod = importlib.import_module(f"src.{module_name}")
        
        # Find all functions that start with "test_"
        for attr_name in dir(mod):
            if attr_name.startswith("test_"):
                test_functions.append(getattr(mod, attr_name))
    
    return test_functions

@pytest.mark.parametrize("test_func", discover_test_functions())
def test_dynamic(test_func):
    """Run all dynamically discovered test functions."""
    test_func()
