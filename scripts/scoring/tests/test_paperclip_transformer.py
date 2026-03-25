"""
Tests for Paperclip Data Transformer.

Run with: python test_paperclip_transformer.py
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperclip_transformer import (
    PaperclipTransformer,
    TransformedTask,
    TransformedComment,
    TransformedAgent,
    TaskStatus,
    TaskType,
)


class TestTaskStatusNormalization(unittest.TestCase):
    """Test task status normalization."""

    def setUp(self):
        self.transformer = PaperclipTransformer()

    def test_todo_variations(self):
        """Test various todo status strings."""
        self.assertEqual(self.transformer._normalize_status("todo"), TaskStatus.TODO)
        self.assertEqual(self.transformer._normalize_status("backlog"), TaskStatus.TODO)
        self.assertEqual(self.transformer._normalize_status("open"), TaskStatus.TODO)

    def test_in_progress_variations(self):
        """Test various in-progress status strings."""
        self.assertEqual(
            self.transformer._normalize_status("in_progress"), TaskStatus.IN_PROGRESS
        )
        self.assertEqual(
            self.transformer._normalize_status("started"), TaskStatus.IN_PROGRESS
        )
        self.assertEqual(
            self.transformer._normalize_status("active"), TaskStatus.IN_PROGRESS
        )

    def test_done_variations(self):
        """Test various done status strings."""
        self.assertEqual(self.transformer._normalize_status("done"), TaskStatus.DONE)
        self.assertEqual(
            self.transformer._normalize_status("completed"), TaskStatus.DONE
        )
        self.assertEqual(self.transformer._normalize_status("closed"), TaskStatus.DONE)

    def test_failed_variations(self):
        """Test various failed status strings."""
        self.assertEqual(
            self.transformer._normalize_status("failed"), TaskStatus.FAILED
        )
        self.assertEqual(self.transformer._normalize_status("error"), TaskStatus.FAILED)
        self.assertEqual(
            self.transformer._normalize_status("rejected"), TaskStatus.FAILED
        )

    def test_empty_status_defaults_todo(self):
        """Test empty status defaults to todo."""
        self.assertEqual(self.transformer._normalize_status(""), TaskStatus.TODO)
        self.assertEqual(self.transformer._normalize_status(None), TaskStatus.TODO)


class TestTaskTypeNormalization(unittest.TestCase):
    """Test task type normalization."""

    def setUp(self):
        self.transformer = PaperclipTransformer()

    def test_code_variations(self):
        """Test various code task types."""
        self.assertEqual(self.transformer._normalize_task_type("code"), TaskType.CODE)
        self.assertEqual(
            self.transformer._normalize_task_type("programming"), TaskType.CODE
        )
        self.assertEqual(
            self.transformer._normalize_task_type("development"), TaskType.CODE
        )

    def test_research_variations(self):
        """Test various research task types."""
        self.assertEqual(
            self.transformer._normalize_task_type("research"), TaskType.RESEARCH
        )
        self.assertEqual(
            self.transformer._normalize_task_type("investigation"), TaskType.RESEARCH
        )

    def test_devops_variations(self):
        """Test various devops task types."""
        self.assertEqual(
            self.transformer._normalize_task_type("devops"), TaskType.DEVOPS
        )
        self.assertEqual(
            self.transformer._normalize_task_type("infrastructure"), TaskType.DEVOPS
        )
        self.assertEqual(
            self.transformer._normalize_task_type("deployment"), TaskType.DEVOPS
        )

    def test_unknown_defaults_general(self):
        """Test unknown types default to general."""
        self.assertEqual(
            self.transformer._normalize_task_type("unknown"), TaskType.GENERAL
        )
        self.assertEqual(self.transformer._normalize_task_type(""), TaskType.GENERAL)


class TestDatetimeParsing(unittest.TestCase):
    """Test datetime parsing."""

    def setUp(self):
        self.transformer = PaperclipTransformer()

    def test_iso_format(self):
        """Test ISO format parsing."""
        dt = self.transformer._parse_datetime("2024-03-21T14:30:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 21)

    def test_iso_format_with_z(self):
        """Test ISO format with Z suffix."""
        dt = self.transformer._parse_datetime("2024-03-21T14:30:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)

    def test_datetime_object(self):
        """Test passing datetime object."""
        original = datetime(2024, 3, 21, 14, 30)
        dt = self.transformer._parse_datetime(original)
        self.assertEqual(dt, original)

    def test_invalid_returns_none(self):
        """Test invalid datetime returns None."""
        dt = self.transformer._parse_datetime("invalid")
        self.assertIsNone(dt)

    def test_none_returns_none(self):
        """Test None returns None."""
        dt = self.transformer._parse_datetime(None)
        self.assertIsNone(dt)


class TestTaskTransformation(unittest.TestCase):
    """Test task transformation."""

    def setUp(self):
        self.transformer = PaperclipTransformer(company_id="test-company")

    def test_basic_transformation(self):
        """Test basic task transformation."""
        paperclip_task = {
            "id": "task-123",
            "title": "Test Task",
            "description": "A test task",
            "agent_id": "agent-1",
            "agent_name": "Test Agent",
            "status": "in_progress",
            "type": "code",
            "created_at": "2024-03-21T14:30:00",
            "updated_at": "2024-03-21T15:30:00",
            "budget": 1000,
            "priority": "high",
            "tags": ["python", "api"],
        }

        transformed = self.transformer.transform_task(paperclip_task)

        self.assertEqual(transformed.id, "task-123")
        self.assertEqual(transformed.title, "Test Task")
        self.assertEqual(transformed.agent_id, "agent-1")
        self.assertEqual(transformed.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(transformed.task_type, TaskType.CODE)
        self.assertEqual(transformed.budget, 1000)
        self.assertEqual(transformed.priority, "high")

    def test_complexity_calculation(self):
        """Test complexity score calculation."""
        simple_task = {
            "budget": 50,
            "priority": "low",
            "tags": [],
        }

        complex_task = {
            "budget": 1500,
            "priority": "high",
            "tags": ["complex", "architecture"],
        }

        simple_score = self.transformer._calculate_complexity(simple_task)
        complex_score = self.transformer._calculate_complexity(complex_task)

        self.assertEqual(simple_score, 1.0)
        self.assertGreater(complex_score, 3.0)  # Budget + priority + tag bonus

    def test_duration_calculation(self):
        """Test duration calculation."""
        task = {
            "created_at": "2024-03-21T10:00:00",
            "completed_at": "2024-03-21T12:30:00",
        }

        duration = self.transformer._calculate_duration(task)
        self.assertIsNotNone(duration)
        self.assertAlmostEqual(duration, 2.5, places=1)

    def test_skills_extraction(self):
        """Test skill extraction from tags."""
        tags = ["python", "javascript", "urgent", "api", "aws"]
        skills = self.transformer._extract_skills_from_tags(tags)

        # Should extract known skills
        self.assertIn("python", skills)
        self.assertIn("javascript", skills)
        self.assertIn("aws", skills)

        # Should not extract non-skills
        self.assertNotIn("urgent", skills)


class TestCommentTransformation(unittest.TestCase):
    """Test comment transformation."""

    def setUp(self):
        self.transformer = PaperclipTransformer()

    def test_basic_transformation(self):
        """Test basic comment transformation."""
        paperclip_comment = {
            "id": "comment-123",
            "issue_id": "task-456",
            "agent_id": "agent-1",
            "agent_name": "Test Agent",
            "body": "This is a comment",
            "created_at": "2024-03-21T14:30:00",
        }

        transformed = self.transformer.transform_comment(paperclip_comment)

        self.assertEqual(transformed.id, "comment-123")
        self.assertEqual(transformed.issue_id, "task-456")
        self.assertEqual(transformed.agent_id, "agent-1")
        self.assertEqual(transformed.word_count, 4)

    def test_code_block_detection(self):
        """Test code block detection in comments."""
        comment_with_code = {
            "id": "comment-1",
            "issue_id": "task-1",
            "agent_id": "agent-1",
            "body": "Here is the fix:\n```python\nprint('hello')\n```",
            "created_at": "2024-03-21T14:30:00",
        }

        transformed = self.transformer.transform_comment(comment_with_code)
        self.assertTrue(transformed.has_code_block)

    def test_output_detection(self):
        """Test output/result detection in comments."""
        comment_with_output = {
            "id": "comment-1",
            "issue_id": "task-1",
            "agent_id": "agent-1",
            "body": "Result: Success!\nOutput: File created",
            "created_at": "2024-03-21T14:30:00",
        }

        transformed = self.transformer.transform_comment(comment_with_output)
        self.assertTrue(transformed.has_output)


class TestAgentTransformation(unittest.TestCase):
    """Test agent transformation."""

    def setUp(self):
        self.transformer = PaperclipTransformer(company_id="test-company")

    def test_basic_transformation(self):
        """Test basic agent transformation."""
        paperclip_agent = {
            "id": "agent-123",
            "name": "Test Agent",
            "company_id": "test-company",
            "role": "developer",
            "description": "A test agent",
            "created_at": "2024-01-01T00:00:00",
        }

        transformed = self.transformer.transform_agent(paperclip_agent)

        self.assertEqual(transformed.id, "agent-123")
        self.assertEqual(transformed.name, "Test Agent")
        self.assertEqual(transformed.role, "developer")
        self.assertEqual(transformed.company_id, "test-company")

    def test_metrics_enrichment(self):
        """Test agent metrics enrichment from tasks."""
        paperclip_agent = {
            "id": "agent-123",
            "name": "Test Agent",
        }

        now = datetime.now()
        tasks = [
            {
                "id": "task-1",
                "status": "done",
                "budget": 100,
                "created_at": now.isoformat(),
                "tags": ["python"],
            },
            {
                "id": "task-2",
                "status": "failed",
                "budget": 50,
                "created_at": now.isoformat(),
                "tags": ["javascript"],
            },
            {
                "id": "task-3",
                "status": "done",
                "budget": 200,
                "created_at": now.isoformat(),
                "tags": ["api"],
            },
        ]

        transformed = self.transformer.transform_agent(paperclip_agent, tasks)

        self.assertEqual(transformed.total_tasks, 3)
        self.assertEqual(transformed.completed_tasks, 2)
        self.assertEqual(transformed.failed_tasks, 1)
        self.assertEqual(transformed.total_revenue, 350)
        self.assertEqual(transformed.success_rate, 2 / 3)

    def test_time_series_calculation(self):
        """Test time series metrics calculation."""
        paperclip_agent = {"id": "agent-123", "name": "Test Agent"}

        now = datetime.now()
        task_10d = {
            "status": "done",
            "budget": 100,
            "created_at": (now - timedelta(days=10)).isoformat(),
        }
        task_60d = {
            "status": "done",
            "budget": 200,
            "created_at": (now - timedelta(days=60)).isoformat(),
        }
        task_120d = {
            "status": "done",
            "budget": 300,
            "created_at": (now - timedelta(days=120)).isoformat(),
        }

        tasks = [task_10d, task_60d, task_120d]

        transformed = self.transformer.transform_agent(paperclip_agent, tasks)

        # 30d: only task_10d
        self.assertEqual(transformed.tasks_30d, 1)
        self.assertEqual(transformed.revenue_30d, 100)

        # 90d: task_10d + task_60d
        self.assertEqual(transformed.tasks_90d, 2)
        self.assertEqual(transformed.revenue_90d, 300)


class TestBatchTransformation(unittest.TestCase):
    """Test batch transformation methods."""

    def setUp(self):
        self.transformer = PaperclipTransformer()

    def test_transform_tasks(self):
        """Test transforming multiple tasks."""
        tasks = [
            {"id": "task-1", "title": "Task 1", "status": "done"},
            {"id": "task-2", "title": "Task 2", "status": "in_progress"},
            {"id": "task-3", "title": "Task 3", "status": "todo"},
        ]

        transformed = self.transformer.transform_tasks(tasks)

        self.assertEqual(len(transformed), 3)
        self.assertEqual(transformed[0].id, "task-1")
        self.assertEqual(transformed[0].status, TaskStatus.DONE)
        self.assertEqual(transformed[1].status, TaskStatus.IN_PROGRESS)

    def test_transform_comments(self):
        """Test transforming multiple comments."""
        comments = [
            {
                "id": "comment-1",
                "issue_id": "task-1",
                "agent_id": "agent-1",
                "body": "Comment 1",
                "created_at": "2024-03-21T14:30:00",
            },
            {
                "id": "comment-2",
                "issue_id": "task-1",
                "agent_id": "agent-1",
                "body": "Comment 2",
                "created_at": "2024-03-21T14:31:00",
            },
        ]

        transformed = self.transformer.transform_comments(comments)

        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed[0].id, "comment-1")

    def test_transform_agents(self):
        """Test transforming multiple agents."""
        agents = [
            {"id": "agent-1", "name": "Agent 1"},
            {"id": "agent-2", "name": "Agent 2"},
        ]

        transformed = self.transformer.transform_agents(agents)

        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed[0].id, "agent-1")
        self.assertEqual(transformed[1].id, "agent-2")


class TestTransformedDataDict(unittest.TestCase):
    """Test to_dict methods."""

    def test_task_to_dict(self):
        """Test task serialization."""
        task = TransformedTask(
            id="task-1",
            title="Test",
            description="Desc",
            agent_id="agent-1",
            agent_name="Agent",
            company_id="company-1",
            status=TaskStatus.DONE,
            task_type=TaskType.CODE,
            created_at=datetime(2024, 3, 21, 14, 30),
            updated_at=datetime(2024, 3, 21, 15, 30),
            completed_at=datetime(2024, 3, 21, 15, 30),
            budget=100,
            value=100,
            priority="high",
        )

        d = task.to_dict()

        self.assertEqual(d["id"], "task-1")
        self.assertEqual(d["status"], "done")
        self.assertEqual(d["task_type"], "code")
        self.assertEqual(d["budget"], 100)
        self.assertIsNotNone(d["created_at"])

    def test_comment_to_dict(self):
        """Test comment serialization."""
        comment = TransformedComment(
            id="comment-1",
            issue_id="task-1",
            agent_id="agent-1",
            agent_name="Agent",
            body="Test comment",
            created_at=datetime(2024, 3, 21, 14, 30),
            word_count=2,
            has_code_block=True,
        )

        d = comment.to_dict()

        self.assertEqual(d["id"], "comment-1")
        self.assertEqual(d["word_count"], 2)
        self.assertTrue(d["has_code_block"])

    def test_agent_to_dict(self):
        """Test agent serialization."""
        agent = TransformedAgent(
            id="agent-1",
            name="Test Agent",
            company_id="company-1",
            role="developer",
            description="Desc",
            created_at=datetime(2024, 3, 21, 14, 30),
            total_tasks=10,
            completed_tasks=8,
            skills=["python", "api"],
            task_types={"code": 5, "research": 3},
        )

        d = agent.to_dict()

        self.assertEqual(d["id"], "agent-1")
        self.assertEqual(d["metrics"]["total_tasks"], 10)
        self.assertEqual(d["skills"], ["python", "api"])
        self.assertEqual(d["task_types"]["code"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
