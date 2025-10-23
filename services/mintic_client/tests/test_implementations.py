"""Tests for MinTIC Client implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.client import MinTICClient
from app.config import Settings
from app.models import AuthenticateDocumentRequest, RegisterCitizenRequest


@pytest.fixture
def settings():
    """Test settings."""
    return Settings(
        mintic_base_url="https://test-hub.example.com",
        metadata_url="http://metadata:8000",
        citizen_url="http://citizen:8000",
        transfer_url="http://transfer:8000",
        redis_host="localhost",
        redis_port=6379,
        redis_password="",
        redis_ssl=False
    )


@pytest.fixture
def mintic_client(settings):
    """Test MinTIC client."""
    return MinTICClient(settings)


class TestDocumentSync:
    """Test document synchronization functionality."""

    @pytest.mark.asyncio
    async def test_get_local_citizen_documents(self, mintic_client):
        """Test getting local citizen documents."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'documents': [
                    {
                        'id': 'doc1',
                        'title': 'Test Document',
                        'sha256_hash': 'abc123',
                        'size': 1024,
                        'created_at': '2025-01-13T10:00:00Z',
                        'status': 'pending'
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            documents = await mintic_client._get_local_citizen_documents("12345")
            
            assert len(documents) == 1
            assert documents[0]['id'] == 'doc1'
            assert documents[0]['title'] == 'Test Document'

    @pytest.mark.asyncio
    async def test_get_local_citizen_documents_error(self, mintic_client):
        """Test error handling in getting local documents."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Connection error")
            
            documents = await mintic_client._get_local_citizen_documents("12345")
            
            assert documents == []

    @pytest.mark.asyncio
    async def test_validate_document_with_hub(self, mintic_client):
        """Test document validation with hub."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'is_valid': True,
                'status': 'validated'
            }
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await mintic_client.validate_document_with_hub(
                "doc1", "abc123", "12345"
            )
            
            assert result['is_valid'] is True
            assert result['validation_status'] == 'validated'

    @pytest.mark.asyncio
    async def test_validate_document_with_hub_error(self, mintic_client):
        """Test document validation error handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Network error")
            
            result = await mintic_client.validate_document_with_hub(
                "doc1", "abc123", "12345"
            )
            
            assert result['is_valid'] is False
            assert result['validation_status'] == 'error'

    @pytest.mark.asyncio
    async def test_sync_citizen_documents(self, mintic_client):
        """Test citizen document synchronization."""
        with patch.object(mintic_client, '_get_local_citizen_documents') as mock_get_docs, \
             patch.object(mintic_client, 'authenticate_document') as mock_auth, \
             patch.object(mintic_client, '_update_document_status') as mock_update, \
             patch.object(mintic_client, 'redis_client') as mock_redis:
            
            # Mock local documents
            mock_get_docs.return_value = [
                {
                    'id': 'doc1',
                    'title': 'Test Document',
                    'download_url': 'https://example.com/doc1',
                    'sha256_hash': 'abc123'
                }
            ]
            
            # Mock authentication response
            mock_auth.return_value = MagicMock(success=True, data={'status': 'authenticated'})
            
            # Mock Redis
            mock_redis.setex = AsyncMock()
            
            result = await mintic_client.sync_citizen_documents("12345")
            
            assert result['synced_count'] == 1
            assert result['failed_count'] == 0
            mock_auth.assert_called_once()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_citizen_sync_status_cached(self, mintic_client):
        """Test getting cached sync status."""
        with patch.object(mintic_client, 'redis_client') as mock_redis:
            mock_redis.get.return_value = {
                'last_sync': '2025-01-13T10:00:00Z',
                'status': 'completed',
                'documents_synced': 5,
                'pending_sync': 0
            }
            
            result = await mintic_client.get_citizen_sync_status("12345")
            
            assert result['status'] == 'completed'
            assert result['documents_synced'] == 5

    @pytest.mark.asyncio
    async def test_get_citizen_sync_status_from_service(self, mintic_client):
        """Test getting sync status from metadata service."""
        with patch.object(mintic_client, 'redis_client') as mock_redis, \
             patch('httpx.AsyncClient') as mock_client:
            
            # Mock Redis cache miss
            mock_redis.get.return_value = None
            
            # Mock metadata service response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'last_sync': '2025-01-13T10:00:00Z',
                'status': 'completed',
                'documents_synced': 3,
                'pending_sync': 0
            }
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            # Mock Redis setex
            mock_redis.setex = AsyncMock()
            
            result = await mintic_client.get_citizen_sync_status("12345")
            
            assert result['status'] == 'completed'
            assert result['documents_synced'] == 3
            mock_redis.setex.assert_called_once()


class TestNotificationHandlers:
    """Test notification handling functionality."""

    @pytest.mark.asyncio
    async def test_handle_document_authentication(self, mintic_client):
        """Test document authentication notification handler."""
        with patch.object(mintic_client, '_update_document_status') as mock_update:
            payload = {
                'document_id': 'doc1',
                'citizen_id': '12345',
                'authentication_result': {'status': 'authenticated'}
            }
            
            await mintic_client.handle_document_authentication(payload)
            
            mock_update.assert_called_once_with('doc1', 'authenticated', {'status': 'authenticated'})

    @pytest.mark.asyncio
    async def test_handle_citizen_update(self, mintic_client):
        """Test citizen update notification handler."""
        with patch.object(mintic_client, '_update_citizen_data') as mock_update:
            payload = {
                'citizen_id': '12345',
                'update_type': 'profile_update',
                'data': {'name': 'New Name'}
            }
            
            await mintic_client.handle_citizen_update(payload)
            
            mock_update.assert_called_once_with('12345', 'profile_update', payload)

    @pytest.mark.asyncio
    async def test_handle_operator_status_change(self, mintic_client):
        """Test operator status change notification handler."""
        with patch.object(mintic_client, '_update_operator_status') as mock_update:
            payload = {
                'operator_id': 'op1',
                'status': 'active'
            }
            
            await mintic_client.handle_operator_status_change(payload)
            
            mock_update.assert_called_once_with('op1', 'active')

    @pytest.mark.asyncio
    async def test_handle_transfer_completion(self, mintic_client):
        """Test transfer completion notification handler."""
        with patch.object(mintic_client, '_update_transfer_status') as mock_update:
            payload = {
                'transfer_id': 'transfer1',
                'status': 'completed',
                'result': {'success': True}
            }
            
            await mintic_client.handle_transfer_completion(payload)
            
            mock_update.assert_called_once_with('transfer1', 'completed', {'success': True})


class TestServiceUpdates:
    """Test service update functionality."""

    @pytest.mark.asyncio
    async def test_update_document_status(self, mintic_client):
        """Test updating document status."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
            
            await mintic_client._update_document_status(
                'doc1', 'authenticated', {'status': 'authenticated'}
            )
            
            # Verify the call was made
            mock_client.return_value.__aenter__.return_value.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_citizen_data(self, mintic_client):
        """Test updating citizen data."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
            
            await mintic_client._update_citizen_data(
                '12345', 'profile_update', {'name': 'New Name'}
            )
            
            # Verify the call was made
            mock_client.return_value.__aenter__.return_value.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_operator_status(self, mintic_client):
        """Test updating operator status."""
        with patch.object(mintic_client, '_cache_operator_status') as mock_cache:
            await mintic_client._update_operator_status('op1', 'active')
            
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_transfer_status(self, mintic_client):
        """Test updating transfer status."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
            
            await mintic_client._update_transfer_status(
                'transfer1', 'completed', {'success': True}
            )
            
            # Verify the call was made
            mock_client.return_value.__aenter__.return_value.put.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
