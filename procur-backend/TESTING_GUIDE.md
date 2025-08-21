# 🧪 Testing Guide for Procur Backend

This guide explains how to use the comprehensive testing framework we've set up for the Procur backend.

## 🚀 Quick Start

### Run All Tests
```bash
python run_tests.py all
```

### Run Specific Test Categories
```bash
python run_tests.py unit          # Unit tests only
python run_tests.py security      # Security tests only
python run_tests.py dependencies  # Dependency tests only
python run_tests.py endpoints     # API endpoint tests only
```

### Run with Coverage
```bash
python run_tests.py coverage
```

### Run Code Quality Checks
```bash
python run_tests.py lint
```

## 📁 Test Structure

```
procur-backend/
├── procur/tests/
│   ├── __init__.py
│   ├── conftest.py              # Test configuration and fixtures
│   ├── test_dependencies.py     # Security dependency tests
│   └── test_api_endpoints.py   # API endpoint tests
├── pytest.ini                   # Pytest configuration
├── run_tests.py                 # Test runner script
└── TESTING_GUIDE.md            # This guide
```

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- **Test Discovery**: Automatically finds tests in `procur/tests/`
- **Async Support**: Configured for async/await testing
- **Markers**: Predefined markers for test categorization
- **Warnings**: Suppresses deprecation warnings during testing

### Test Fixtures (`conftest.py`)
The testing framework provides these key fixtures:

#### 🔐 Authentication Fixtures
- `mock_firebase`: Mocks all Firebase services
- `valid_token_payload`: Valid Firebase token for testing
- `expired_token_payload`: Expired token for testing
- `test_user_data`: Regular user data
- `test_admin_user_data`: Admin user data

#### 📊 Data Fixtures
- `test_group_data`: Sample group data
- `mock_user_document`: Mock Firestore user document
- `mock_admin_document`: Mock Firestore admin document
- `mock_group_document`: Mock Firestore group document

#### 🧪 Testing Fixtures
- `client`: FastAPI test client
- `event_loop`: Async event loop for testing

## 🧪 Test Categories

### 1. Security Dependency Tests (`test_dependencies.py`)

#### Authentication Tests
- ✅ Valid token authentication
- ❌ Expired token rejection
- ❌ Disabled user rejection
- ❌ Invalid token handling

#### Permission Tests
- ✅ Admin access to admin-only operations
- ❌ Non-admin access rejection
- ✅ Member access to member operations
- ❌ Non-member access rejection

#### Group Privacy Tests
- ✅ Public group access
- ✅ Private group member access
- ❌ Private group non-member rejection

### 2. API Endpoint Tests (`test_api_endpoints.py`)

#### Group Endpoints
- ✅ Admin can handle join requests
- ❌ Non-admin cannot handle join requests
- ✅ Users can request to join groups
- ❌ Cannot join inactive groups

#### Invitation Endpoints
- ✅ Admin can deactivate invitations
- ❌ Non-admin cannot deactivate invitations
- ✅ Admin can regenerate invitation tokens
- ❌ Non-admin cannot regenerate tokens

#### Upload Endpoints
- ✅ Admin can get upload URLs
- ❌ Non-admin cannot get upload URLs

#### Authentication Endpoints
- ❌ Unauthenticated access rejection
- ❌ Invalid token rejection

## 🎯 Running Tests

### Using the Test Runner Script
```bash
# Navigate to the backend directory
cd procur-backend

# Run all tests
python run_tests.py all

# Run specific test categories
python run_tests.py security
python run_tests.py endpoints

# Run with coverage
python run_tests.py coverage

# Run code quality checks
python run_tests.py lint
```

### Using Pytest Directly
```bash
# Run all tests
python -m pytest procur/tests/ -v

# Run specific test file
python -m pytest procur/tests/test_dependencies.py -v

# Run specific test class
python -m pytest procur/tests/test_dependencies.py::TestGetCurrentUser -v

# Run specific test method
python -m pytest procur/tests/test_dependencies.py::TestGetCurrentUser::test_valid_token_success -v

# Run with coverage
python -m pytest procur/tests/ --cov=procur --cov-report=html
```

## 🔍 Understanding Test Results

### ✅ Test Passes
- **Green dots**: Individual tests passed
- **Summary**: Shows total tests run and passed

### ❌ Test Failures
- **Red F**: Individual test failed
- **Error details**: Shows what went wrong
- **Traceback**: Points to the exact failure location

### ⚠️ Test Warnings
- **Yellow W**: Test passed but with warnings
- **Warning details**: Shows what to be aware of

## 🛠️ Writing New Tests

### 1. Test File Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestYourFeature:
    """Test description"""
    
    @pytest.mark.asyncio
    async def test_specific_scenario(self, mock_firebase, test_user_data):
        """Test specific scenario description"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'test_user_123'}
        
        # Test logic
        result = await your_function()
        
        # Assertions
        assert result == expected_value
```

### 2. Using Fixtures
```python
def test_with_fixtures(self, client, mock_firebase, test_user_data):
    """Test using multiple fixtures"""
    # Use client for HTTP requests
    response = client.get("/api/endpoint")
    
    # Use mock_firebase for Firebase mocking
    mock_firebase['verify_token'].return_value = test_user_data
    
    # Use test_user_data for consistent test data
    assert response.status_code == 200
```

### 3. Mocking External Services
```python
@patch('procur.core.firebase.verify_firebase_token')
def test_with_mock(self, mock_verify):
    """Test with specific mocking"""
    mock_verify.return_value = {'uid': 'test_user'}
    
    # Your test logic here
    result = verify_token("fake_token")
    
    assert result['uid'] == 'test_user'
    mock_verify.assert_called_once_with("fake_token")
```

## 🚨 Common Testing Issues

### 1. Import Errors
**Problem**: `ModuleNotFoundError: No module named 'procur'`
**Solution**: Ensure you're running tests from the `procur-backend` directory

### 2. Async Test Failures
**Problem**: Tests fail with async-related errors
**Solution**: Use `@pytest.mark.asyncio` decorator for async tests

### 3. Mock Configuration Issues
**Problem**: Mocks not working as expected
**Solution**: Check that mocks are set up before the function call

### 4. Fixture Scope Issues
**Problem**: Fixtures not persisting between tests
**Solution**: Check fixture scope (function, class, module, session)

## 📊 Coverage Reports

### Generate Coverage Report
```bash
python run_tests.py coverage
```

### View Coverage Report
- **Terminal**: Shows coverage summary in terminal
- **HTML**: Open `htmlcov/index.html` in browser for detailed view

### Coverage Metrics
- **Line Coverage**: Percentage of code lines executed
- **Branch Coverage**: Percentage of code branches executed
- **Function Coverage**: Percentage of functions called

## 🔒 Security Testing Best Practices

### 1. Test All Permission Levels
- ✅ Admin users can access admin operations
- ❌ Regular users cannot access admin operations
- ✅ Users can access their own resources
- ❌ Users cannot access others' resources

### 2. Test Edge Cases
- Expired tokens
- Disabled users
- Invalid group IDs
- Malformed requests

### 3. Test Authentication Bypass
- Missing authentication headers
- Invalid authentication tokens
- Expired authentication tokens

## 🎉 Next Steps

### 1. Run the Test Suite
```bash
python run_tests.py all
```

### 2. Review Test Results
- Identify any failing tests
- Understand what each test validates
- Check coverage reports

### 3. Add More Tests
- Test additional edge cases
- Add integration tests
- Test error handling scenarios

### 4. Continuous Integration
- Set up automated testing in CI/CD
- Run tests on every commit
- Maintain high test coverage

## 📞 Getting Help

If you encounter issues with the testing framework:

1. **Check the logs**: Look for detailed error messages
2. **Review test configuration**: Ensure `pytest.ini` is correct
3. **Verify dependencies**: Ensure all testing packages are installed
4. **Check file paths**: Ensure tests are in the correct directory structure

The testing framework is designed to be comprehensive and easy to use. Start with running all tests to get familiar with the system, then dive into specific test categories as needed.
