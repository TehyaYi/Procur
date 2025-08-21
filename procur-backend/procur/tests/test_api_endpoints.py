import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from procur.models.schemas import UserResponse, UserRole
from datetime import datetime

class TestGroupEndpoints:
    """Test group-related endpoints for security"""
    
    @pytest.mark.asyncio
    async def test_mock_debug(self, client, mock_firebase):
        """Debug test to check if mocks are working"""
        # Test if the mock is working
        from procur.core.dependencies import verify_firebase_token
        
        # Call the function directly to see what it returns
        result = verify_firebase_token("test_token")
        print(f"Mock result: {result}")
        print(f"Mock result type: {type(result)}")
        print(f"Mock result keys: {result.keys() if hasattr(result, 'keys') else 'No keys method'}")
        
        # Check if the mock was called
        assert mock_firebase['verify_token'].called
        assert result['uid'] == 'test_user_123'
    
    @pytest.mark.asyncio
    async def test_user_data_debug(self, client, mock_firebase, mock_admin_document):
        """Debug test to check what user_data looks like"""
        # Setup the mock to return the admin document
        mock_firebase['document'].get.return_value = mock_admin_document
        
        # Call the get_current_user function directly to see what happens
        from procur.core.dependencies import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create a mock credentials object
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "test_token"
        
        # Create a mock request
        mock_request = Mock()
        mock_request.client.host = "testclient"
        mock_request.headers.get.return_value = "testclient"
        
        try:
            result = await get_current_user(mock_credentials, mock_request)
            print(f"UserResponse result: {result}")
            print(f"UserResponse type: {type(result)}")
        except Exception as e:
            print(f"Exception occurred: {e}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
    
    @pytest.mark.asyncio
    async def test_handle_join_request_admin_success(self, client, mock_firebase, test_group_data, mock_admin_document):
        """Test admin can handle join requests"""
        # Setup mocks
        # The verify_firebase_token mock is already set up in conftest.py
        # We just need to set up the user document mock
        mock_firebase['document'].get.return_value = mock_admin_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Mock join request document
        mock_join_request_doc = Mock()
        mock_join_request_doc.exists = True
        mock_join_request_doc.to_dict.return_value = {
            'id': 'request_123',
            'group_id': 'test_group_789',
            'user_id': 'test_user_123',
            'status': 'pending',
            'message': 'Please approve my request'
        }
        
        # Mock member document (admin)
        mock_member_doc = Mock()
        mock_member_doc.exists = True
        mock_member_doc.to_dict.return_value = {
            'user_id': 'test_user_123',
            'role': 'admin',
            'joined_at': datetime.now()
        }
        
        # Setup Firestore mocks with proper chaining
        # For join request: db.collection('join_requests').document(request_id).get()
        mock_join_request_collection = Mock()
        mock_join_request_collection.document.return_value = mock_join_request_doc
        
        # For member check: db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        mock_members_collection = Mock()
        mock_members_collection.document.return_value = mock_member_doc
        
        # Setup the chain
        mock_firebase['db'].collection.side_effect = lambda collection_name: {
            'join_requests': mock_join_request_collection,
            'groups': mock_firebase['collection']
        }.get(collection_name, mock_firebase['collection'])
        
        mock_firebase['collection'].document.return_value = mock_group_doc
        mock_group_doc.collection.return_value = mock_members_collection
        
        # Test the endpoint
        response = client.patch(
            "/api/groups/join-requests/request_123",
            json={"status": "approved"},
            headers={"Authorization": "Bearer admin_token_123"}
        )
        
        # Should succeed for admin
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_handle_join_request_non_admin_failure(self, client, mock_firebase, test_group_data, mock_user_document):
        """Test non-admin cannot handle join requests"""
        # Setup mocks - use default mock value from conftest.py
        mock_firebase['document'].get.return_value = mock_user_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.patch(
            "/api/groups/join-requests/request_123",
            json={"status": "approved"},
            headers={"Authorization": "Bearer user_token_123"}
        )
        
        # Should fail for non-admin
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_request_join_group_success(self, client, mock_firebase, test_group_data, mock_user_document):
        """Test user can request to join a group"""
        # Setup mocks - use default mock value from conftest.py
        mock_firebase['document'].get.return_value = mock_user_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.post(
            "/api/groups/test_group_789/join-request",
            headers={"Authorization": "Bearer user_token_123"}
        )
        
        # Should succeed
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_request_join_inactive_group_failure(self, client, mock_firebase, mock_user_document):
        """Test cannot join inactive group"""
        # Setup mocks - use default mock value from conftest.py
        mock_firebase['document'].get.return_value = mock_user_document
        
        # Mock inactive group document
        inactive_group_data = {
            'id': 'inactive_group_999',
            'name': 'Inactive Group',
            'is_active': False
        }
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = inactive_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.post(
            "/api/groups/inactive_group_999/join-request",
            headers={"Authorization": "Bearer user_token_123"}
        )
        
        # Should fail for inactive group
        assert response.status_code == 400

class TestInvitationEndpoints:
    """Test invitation-related endpoints for security"""
    
    @pytest.mark.asyncio
    async def test_deactivate_invitation_admin_success(self, client, mock_firebase, test_group_data, mock_admin_document):
        """Test admin can deactivate invitations"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'admin_user_456', 'disabled': False}
        mock_firebase['document'].get.return_value = mock_admin_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.delete(
            "/api/invitations/invitation_123",
            headers={"Authorization": "Bearer admin_token_123"}
        )
        
        # Should succeed for admin
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_deactivate_invitation_non_admin_failure(self, client, mock_firebase, test_group_data, mock_user_document):
        """Test non-admin cannot deactivate invitations"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'test_user_123', 'disabled': False}
        mock_firebase['document'].get.return_value = mock_user_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.delete(
            "/api/invitations/invitation_123",
            headers={"Authorization": "Bearer user_token_123"}
        )
        
        # Should fail for non-admin
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_regenerate_invitation_token_admin_success(self, client, mock_firebase, test_group_data, mock_admin_document):
        """Test admin can regenerate invitation tokens"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'admin_user_456', 'disabled': False}
        mock_firebase['document'].get.return_value = mock_admin_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.post(
            "/api/invitations/invitation_123/regenerate",
            headers={"Authorization": "Bearer admin_token_123"}
        )
        
        # Should succeed for admin
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_regenerate_invitation_token_non_admin_failure(self, client, mock_firebase, test_group_data, mock_user_document):
        """Test non-admin cannot regenerate invitation tokens"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'test_user_123', 'disabled': False}
        mock_firebase['document'].get.return_value = mock_user_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.post(
            "/api/invitations/invitation_123/regenerate",
            headers={"Authorization": "Bearer user_token_123"}
        )
        
        # Should fail for non-admin
        assert response.status_code == 403

class TestUploadEndpoints:
    """Test upload-related endpoints for security"""
    
    @pytest.mark.asyncio
    async def test_get_upload_url_admin_success(self, client, mock_firebase, test_group_data, mock_admin_document):
        """Test admin can get upload URLs"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'admin_user_456', 'disabled': False}
        mock_firebase['document'].get.return_value = mock_admin_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.post(
            "/api/uploads/upload-url",
            json={"group_id": "test_group_789", "filename": "test.pdf"},
            headers={"Authorization": "Bearer admin_token_123"}
        )
        
        # Should succeed for admin
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_upload_url_non_admin_failure(self, client, mock_firebase, test_group_data, mock_user_document):
        """Test non-admin cannot get upload URLs"""
        # Setup mocks
        mock_firebase['verify_token'].return_value = {'uid': 'test_user_123', 'disabled': False}
        mock_firebase['document'].get.return_value = mock_user_document
        
        # Mock group document
        mock_group_doc = Mock()
        mock_group_doc.exists = True
        mock_group_doc.to_dict.return_value = test_group_data
        
        # Setup Firestore mocks
        mock_firebase['collection'].document.return_value = mock_group_doc
        
        # Test the endpoint
        response = client.post(
            "/api/uploads/upload-url",
            json={"group_id": "test_group_789", "filename": "test.pdf"},
            headers={"Authorization": "Bearer user_token_123"}
        )
        
        # Should fail for non-admin
        assert response.status_code == 403

class TestAuthenticationEndpoints:
    """Test authentication endpoints"""
    
    def test_unauthenticated_access_failure(self, client):
        """Test endpoints fail without authentication"""
        # Test various endpoints without auth headers
        endpoints = [
            "/api/groups/test_group_789/join-requests/request_123/handle",
            "/api/invitations/invitation_123",
            "/api/uploads/upload-url"
        ]
        
        for endpoint in endpoints:
            response = client.post(endpoint, json={})
            assert response.status_code == 401  # Unauthorized
    
    def test_invalid_token_failure(self, client):
        """Test endpoints fail with invalid tokens"""
        # Test with invalid token
        response = client.post(
            "/api/groups/test_group_789/join-requests/request_123/handle",
            json={"action": "approve"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401  # Unauthorized
