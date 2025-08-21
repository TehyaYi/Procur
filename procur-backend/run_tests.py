#!/usr/bin/env python3
"""
Test Runner Script for Procur Backend
Provides easy commands to run different types of tests
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and display the result"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Running: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False

def main():
    """Main test runner function"""
    print("🧪 Procur Backend Test Runner")
    print("=" * 40)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python run_tests.py [command]")
        print("\nCommands:")
        print("  all          - Run all tests")
        print("  unit         - Run unit tests only")
        print("  security     - Run security tests only")
        print("  dependencies - Run dependency tests only")
        print("  endpoints    - Run API endpoint tests only")
        print("  coverage     - Run tests with coverage report")
        print("  lint         - Run code linting")
        print("  help         - Show this help message")
        return
    
    command = sys.argv[1].lower()
    
    if command == "help":
        print("\nAvailable Commands:")
        print("  all          - Run all tests")
        print("  unit         - Run unit tests only")
        print("  security     - Run security tests only")
        print("  dependencies - Run dependency tests only")
        print("  endpoints    - Run API endpoint tests only")
        print("  coverage     - Run tests with coverage report")
        print("  lint         - Run code linting")
        print("  help         - Show this help message")
        return
    
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    if command == "all":
        success = run_command("python -m pytest procur/tests/ -v", "All Tests")
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
    
    elif command == "unit":
        success = run_command("python -m pytest procur/tests/test_dependencies.py -v", "Unit Tests")
        if success:
            print("\n🎉 Unit tests passed!")
        else:
            print("\n💥 Unit tests failed!")
            sys.exit(1)
    
    elif command == "security":
        success = run_command("python -m pytest procur/tests/test_dependencies.py::TestGetCurrentUser -v", "Security Tests")
        if success:
            print("\n🎉 Security tests passed!")
        else:
            print("\n💥 Security tests failed!")
            sys.exit(1)
    
    elif command == "dependencies":
        success = run_command("python -m pytest procur/tests/test_dependencies.py -v", "Dependency Tests")
        if success:
            print("\n🎉 Dependency tests passed!")
        else:
            print("\n💥 Dependency tests failed!")
            sys.exit(1)
    
    elif command == "endpoints":
        success = run_command("python -m pytest procur/tests/test_api_endpoints.py -v", "API Endpoint Tests")
        if success:
            print("\n🎉 API endpoint tests passed!")
        else:
            print("\n💥 API endpoint tests failed!")
            sys.exit(1)
    
    elif command == "coverage":
        success = run_command("python -m pytest procur/tests/ --cov=procur --cov-report=html --cov-report=term", "Tests with Coverage")
        if success:
            print("\n🎉 Coverage tests passed!")
            print("📊 Coverage report generated in htmlcov/ directory")
        else:
            print("\n💥 Coverage tests failed!")
            sys.exit(1)
    
    elif command == "lint":
        print("\n🔍 Running Code Linting...")
        lint_commands = [
            ("black --check procur/", "Code Formatting Check"),
            ("isort --check-only procur/", "Import Sorting Check"),
            ("flake8 procur/", "Code Quality Check"),
            ("mypy procur/", "Type Checking")
        ]
        
        all_passed = True
        for cmd, desc in lint_commands:
            if not run_command(cmd, desc):
                all_passed = False
        
        if all_passed:
            print("\n🎉 All linting checks passed!")
        else:
            print("\n💥 Some linting checks failed!")
            sys.exit(1)
    
    else:
        print(f"\n❌ Unknown command: {command}")
        print("Use 'python run_tests.py help' to see available commands")
        sys.exit(1)

if __name__ == "__main__":
    main()
