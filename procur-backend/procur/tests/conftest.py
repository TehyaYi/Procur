import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from procur.main import app
from procur.core.firebase import get_firestore_client
from procur.models.schemas import UserResponse, UserRole
from datetime import datetime, timedelta, timezone

# Load test environment configuration
import test_env

# Test client
@pytest.fixture
def client():
    """Test client for FastAPI app with custom headers"""
    # Create test client with custom headers to avoid host validation issues
    return TestClient(app, headers={"Host": "localhost"})

# Mock Firebase dependencies
@pytest.fixture
def mock_firebase():
    """Mock Firebase services for testing"""
    # Import time to get current timestamp
    import time
    current_time = int(time.time())
    
    # Create the mock return value for verify_firebase_token
    mock_token_data = {
        'uid': 'test_user_123', 
        'disabled': False, 
        'iat': current_time
    }
    
    # Patch the function at the module level where it's used
    with patch('procur.core.dependencies.verify_firebase_token') as mock_verify, \
         patch('procur.core.dependencies.get_firestore_client') as mock_firestore, \
         patch('procur.core.dependencies.blacklist_token') as mock_blacklist, \
         patch('procur.core.firebase.verify_firebase_token') as mock_verify_firebase:
        
        # Configure the mocks to return the dictionary directly
        mock_verify.return_value = mock_token_data
        mock_verify_firebase.return_value = mock_token_data
        
        # Create a simple mock that returns basic data
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        # Create mock objects that the tests expect
        mock_collection = Mock()
        mock_document = Mock()
        mock_members_collection = Mock()
        mock_member_document = Mock()
        
        # Set up basic chain for tests that need it
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.collection.return_value = mock_members_collection
        mock_members_collection.document.return_value = mock_member_document
        
        yield {
            'verify_token': mock_verify,
            'verify_firebase': mock_verify_firebase,
            'firestore': mock_firestore,
            'blacklist': mock_blacklist,
            'db': mock_db,
            'collection': mock_collection,
            'document': mock_document,
            'members_collection': mock_members_collection,
            'member_document': mock_member_document
        }

# Test user data
@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        'email': 'test@example.com',
        'display_name': 'Test User',
        'status': 'active',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'is_active': True,
        'role': UserRole.MEMBER
    }

@pytest.fixture
def test_admin_user_data():
    """Sample admin user data for testing"""
    return {
        'email': 'admin@example.com',
        'display_name': 'Admin User',
        'status': 'active',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'is_active': True,
        'role': UserRole.ADMIN
    }

@pytest.fixture
def test_user_data_with_uid():
    """Sample user data with uid for group tests"""
    return {
        'uid': 'test_user_123',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'status': 'active',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'is_active': True,
        'role': UserRole.MEMBER
    }

@pytest.fixture
def test_admin_user_data_with_uid():
    """Sample admin user data with uid for group tests"""
    return {
        'uid': 'admin_user_456',
        'email': 'admin@example.com',
        'display_name': 'Admin User',
        'status': 'active',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'is_active': True,
        'role': UserRole.ADMIN
    }

@pytest.fixture
def test_group_data():
    """Sample group data for testing"""
    return {
        'id': 'test_group_789',
        'name': 'Test Group',
        'description': 'A test group',
        'admin_id': 'admin_user_456',
        'privacy': 'public',
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'member_count': 2
    }

@pytest.fixture
def mock_user_document(test_user_data):
    """Mock Firestore user document"""
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = test_user_data
    return mock_doc

@pytest.fixture
def mock_admin_document(test_admin_user_data):
    """Mock Firestore admin user document"""
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = test_admin_user_data
    return mock_doc

@pytest.fixture
def mock_group_document(test_group_data):
    """Mock Firestore group document"""
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = test_group_data
    return mock_doc

@pytest.fixture
def valid_token_payload():
    """Valid Firebase token payload for testing"""
    return {
        'uid': 'test_user_123',
        'email': 'test@example.com',
        'iat': datetime.now(timezone.utc).timestamp(),
        'exp': (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        'disabled': False
    }

@pytest.fixture
def expired_token_payload():
    """Expired Firebase token payload for testing"""
    return {
        'uid': 'test_user_123',
        'email': 'test@example.com',
        'iat': (datetime.now(timezone.utc) - timedelta(days=2)).timestamp(),
        'exp': (datetime.now(timezone.utc) - timedelta(days=1)).timestamp(),
        'disabled': False
    }

# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
