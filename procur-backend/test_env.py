#!/usr/bin/env python3
"""
Test environment configuration
This file sets environment variables for testing to avoid host validation issues
"""

import os

# Set environment variables for testing
os.environ["ALLOWED_HOSTS"] = '["*"]'
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"

print("🧪 Test environment configured:")
print(f"   ALLOWED_HOSTS: {os.environ.get('ALLOWED_HOSTS')}")
print(f"   ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")
print(f"   DEBUG: {os.environ.get('DEBUG')}")
