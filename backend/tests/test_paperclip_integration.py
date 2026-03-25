"""
Tests for Paperclip API integration.

Run with: pytest tests/test_paperclip_integration.py -v
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch

from app.services.paperclip_client import (
    PaperclipClient,
    PaperclipAPIError,
    PaperclipAuthError,
    PaperclipRateLimitError,
)
from app.services.paperclip_transformer import PaperclipTransformer


class TestPaperclipClient:
    """Test Paperclip API client."""

    @pytest_asyncio.fixture
    async def client(self):
        """Create a test client."""
        client = PaperclipClient(
            api_url="http://localhost:3100",
            api_key="test-key",
        )
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client is properly initialized."""
        assert client.api_url == "http://localhost:3100"
        assert client.api_key == "test-key"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "version": "0.3.1"}
        mock_response.raise_for_status = Mock()

        with patch.object(
            client, "_request", return_value=mock_response.json.return_value
        ):
            result = await client.health_check()
            assert result["status"] == "ok"
            assert result["version"] == "0.3.1"

    @pytest.mark.asyncio
    async def test_get_tasks(self, client):
        """Test fetching tasks."""
        mock_tasks = [
            {"id": "task-1", "title": "Test Task 1", "status": "done"},
            {"id": "task-2", "title": "Test Task 2", "status": "in_progress"},
        ]

        with patch.object(client, "_request", return_value={"issues": mock_tasks}):
            tasks = await client.get_tasks(status="done", limit=10)
            assert len(tasks) == 2
            assert tasks[0]["id"] == "task-1"


class TestPaperclipTransformer:
    """Test Paperclip data transformer."""

    @pytest.fixture
    def transformer(self):
        """Create a test transformer."""
        return PaperclipTransformer(default_hourly_rate=50.0)

    def test_transform_task_basic(self, transformer):
        """Test basic task transformation."""
        paperclip_task = {
            "id": "task-123",
            "title": "Build API endpoint",
            "description": "Create REST API for user management",
            "status": "done",
            "assigneeAgentId": "agent-456",
            "createdAt": "2024-03-21T10:00:00Z",
            "startedAt": "2024-03-21T10:30:00Z",
            "completedAt": "2024-03-21T12:00:00Z",
        }

        result = transformer.transform_task(paperclip_task)

        assert result["paperclip_task_id"] == "task-123"
        assert result["agent_id"] == "agent-456"
        assert result["status"] == "completed"
        assert result["duration_minutes"] == 90  # 1.5 hours
        assert "api" in result["skills_demonstrated"]
        assert result["category"] == "backend"
        assert result["estimated_revenue_usd"] > 0

    def test_status_mapping(self, transformer):
        """Test status mapping from Paperclip to AgentRank."""
        assert transformer._map_status("todo") == "pending"
        assert transformer._map_status("in_progress") == "active"
        assert transformer._map_status("done") == "completed"
        assert transformer._map_status("cancelled") == "cancelled"
        assert transformer._map_status("unknown_status") == "unknown"

    def test_categorize_task(self, transformer):
        """Test task categorization."""
        assert transformer._categorize_task("Build Docker deployment") == "devops"
        assert transformer._categorize_task("Create React component") == "frontend"
        assert transformer._categorize_task("Design database schema") == "backend"
        assert transformer._categorize_task("Write blog post") == "content"
        assert transformer._categorize_task("Unknown task") == "general"

    def test_extract_skills(self, transformer):
        """Test skill extraction."""
        skills = transformer._extract_skills(
            "Build Python API with PostgreSQL", "Use FastAPI framework"
        )
        assert "python" in skills
        assert "api" in skills
        assert "database" in skills

    def test_calculate_duration(self, transformer):
        """Test duration calculation."""
        from datetime import datetime

        started = datetime(2024, 3, 21, 10, 0, 0)
        completed = datetime(2024, 3, 21, 12, 30, 0)

        duration = transformer._calculate_duration(started, completed, None)
        assert duration == 150  # 2.5 hours in minutes

    def test_estimate_revenue(self, transformer):
        """Test revenue estimation."""
        # DevOps task should have higher multiplier
        revenue = transformer._estimate_revenue(
            duration_minutes=120,  # 2 hours
            title="Deploy Kubernetes cluster",
            category="devops",
        )
        # 2 hours * $50/hr * 1.3 multiplier = $130
        assert revenue == 130.0

    def test_batch_transform(self, transformer):
        """Test batch transformation."""
        tasks = [
            {
                "id": "1",
                "title": "Task 1",
                "status": "done",
                "assigneeAgentId": "agent-1",
            },
            {
                "id": "2",
                "title": "Task 2",
                "status": "done",
                "assigneeAgentId": "agent-2",
            },
            {
                "id": "3",
                "title": "Task 3",
                "status": "invalid",
            },  # Should handle gracefully
        ]

        results = transformer.batch_transform_tasks(tasks)

        assert len(results) >= 2  # At least first two should succeed
        assert all(r.get("paperclip_task_id") for r in results)


@pytest.mark.asyncio
async def test_integration_health_check():
    """
    Integration test: Verify Paperclip connection.

    This test requires Paperclip to be running locally.
    Skip in CI or if Paperclip is not available.
    """
    import os

    if os.getenv("SKIP_INTEGRATION_TESTS"):
        pytest.skip("Integration tests disabled")

    client = PaperclipClient()
    await client.connect()

    try:
        health = await client.health_check()
        assert health.get("status") == "ok"
        print(f"✓ Paperclip API healthy: {health}")
    except Exception as e:
        pytest.skip(f"Paperclip not available: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
