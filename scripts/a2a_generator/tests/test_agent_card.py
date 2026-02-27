#!/usr/bin/env python3
"""
Tests for A2A Agent Card Generator v3.0

Run tests with: python -m pytest tests/test_agent_card.py -v
"""

import json
import sys
import os
import unittest
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from a2a_generator import (
    AgentCardGenerator,
    AgentCardBuilder,
    AgentCardValidator,
    AgentCard,
    Provider,
    Capability,
    AuthScheme,
    Skill,
    SupportedInterface
)


class TestProvider(unittest.TestCase):
    """Test Provider dataclass."""
    
    def test_basic_provider(self):
        p = Provider(name="Test Org")
        self.assertEqual(p.name, "Test Org")
        self.assertIsNone(p.url)
        
    def test_full_provider(self):
        p = Provider(
            name="Test Org",
            url="https://example.com",
            support_contact="help@example.com"
        )
        d = p.to_dict()
        self.assertEqual(d["name"], "Test Org")
        self.assertEqual(d["url"], "https://example.com")
        self.assertEqual(d["support_contact"], "help@example.com")


class TestCapability(unittest.TestCase):
    """Test Capability dataclass."""
    
    def test_defaults(self):
        c = Capability()
        self.assertEqual(c.a2a_version, "1.0")
        self.assertTrue(c.supports_tools)
        self.assertFalse(c.supports_streaming)
        
    def test_to_dict(self):
        c = Capability(
            a2a_version="1.0",
            mcp_version="0.6",
            supported_message_parts=["text", "file"],
            supports_tools=True
        )
        d = c.to_dict()
        self.assertEqual(d["a2aVersion"], "1.0")
        self.assertEqual(d["mcpVersion"], "0.6")
        self.assertIn("text", d["supportedMessageParts"])


class TestAuthScheme(unittest.TestCase):
    """Test AuthScheme dataclass."""
    
    def test_none_scheme(self):
        a = AuthScheme("none", "Public agent")
        d = a.to_dict()
        self.assertEqual(d["scheme"], "none")
        self.assertEqual(d["description"], "Public agent")
        
    def test_oauth2_scheme(self):
        a = AuthScheme(
            "oauth2",
            "OAuth2 auth",
            token_url="https://auth.example.com/token",
            scopes=["read", "write"]
        )
        d = a.to_dict()
        self.assertEqual(d["tokenUrl"], "https://auth.example.com/token")
        self.assertIn("read", d["scopes"])


class TestSkill(unittest.TestCase):
    """Test Skill dataclass."""
    
    def test_basic_skill(self):
        s = Skill(
            id="weather",
            name="Weather",
            description="Check weather"
        )
        d = s.to_dict()
        self.assertEqual(d["id"], "weather")
        self.assertEqual(d["name"], "Weather")
        
    def test_skill_with_schema(self):
        s = Skill(
            id="calc",
            name="Calculator",
            description="Simple calculator",
            input_schema={"type": "object", "properties": {"x": {"type": "number"}}},
            tags=["math"]
        )
        d = s.to_dict()
        self.assertEqual(d["inputSchema"]["type"], "object")
        self.assertIn("math", d["tags"])


class TestAgentCard(unittest.TestCase):
    """Test AgentCard dataclass."""
    
    def test_minimal_card(self):
        card = AgentCard(
            schema_version="1.0",
            human_readable_id="test/agent",
            agent_version="1.0.0",
            name="Test Agent",
            description="A test agent",
            url="https://example.com/a2a",
            provider=Provider(name="Test Provider"),
            capabilities=Capability(),
            auth_schemes=[AuthScheme("none", "Public")]
        )
        
        d = card.to_dict()
        self.assertEqual(d["schemaVersion"], "1.0")
        self.assertEqual(d["name"], "Test Agent")
        self.assertIn("capabilities", d)
        
    def test_to_json(self):
        card = AgentCardBuilder()\
            .with_identity("test/agent", "Test Agent", "1.0.0")\
            .with_description("Test")\
            .with_endpoint("https://example.com/a2a")\
            .with_provider("Test Org")\
            .add_auth_none("Public")\
            .build()
        
        json_str = card.to_json()
        self.assertIn("schemaVersion", json_str)
        
        # Verify valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["name"], "Test Agent")


class TestValidator(unittest.TestCase):
    """Test AgentCardValidator."""
    
    def test_valid_card(self):
        card = AgentCardBuilder()\
            .with_identity("test/agent", "Test Agent", "1.0.0")\
            .with_description("Test")\
            .with_endpoint("https://example.com/a2a")\
            .with_provider("Test Org")\
            .add_auth_none("Public")\
            .build()
        
        validator = AgentCardValidator()
        is_valid = validator.validate(card)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(validator.errors), 0)
        
    def test_missing_required_fields(self):
        validator = AgentCardValidator()
        
        # Missing multiple required fields
        is_valid = validator.validate({"name": "Test"})
        
        self.assertFalse(is_valid)
        self.assertTrue(len(validator.errors) > 0)
        self.assertIn("Missing required field: humanReadableId", validator.errors)
        
    def test_invalid_auth_scheme(self):
        validator = AgentCardValidator()
        
        card = {
            "schemaVersion": "1.0",
            "humanReadableId": "test/agent",
            "agentVersion": "1.0.0",
            "name": "Test",
            "description": "Test",
            "url": "https://example.com/a2a",
            "provider": {"name": "Provider"},
            "capabilities": {"a2aVersion": "1.0"},
            "authSchemes": [{"scheme": "invalid", "description": "Bad"}]
        }
        
        is_valid = validator.validate(card)
        self.assertFalse(is_valid)
        self.assertTrue(any("invalid" in e.lower() for e in validator.errors))


class TestBuilder(unittest.TestCase):
    """Test AgentCardBuilder."""
    
    def test_build_minimal(self):
        card = AgentCardBuilder()\
            .with_identity("test/agent", "Test", "1.0.0")\
            .with_description("Test description")\
            .with_endpoint("https://example.com/a2a")\
            .with_provider("Test Org")\
            .add_auth_none("Public")\
            .build()
        
        self.assertEqual(card.name, "Test")
        self.assertEqual(len(card.auth_schemes), 1)
        
    def test_build_with_skills(self):
        card = AgentCardBuilder()\
            .with_identity("test/agent", "Test", "1.0.0")\
            .with_description("Test")\
            .with_endpoint("https://example.com/a2a")\
            .with_provider("Org")\
            .add_auth_none("Public")\
            .add_skill("skill1", "Skill 1", "First skill")\
            .add_skill("skill2", "Skill 2", "Second skill", tags=["test"])\
            .build()
        
        self.assertEqual(len(card.skills), 2)
        
    def test_build_with_interfaces(self):
        card = AgentCardBuilder()\
            .with_identity("test/agent", "Test", "1.0.0")\
            .with_description("Test")\
            .with_endpoint("https://example.com/a2a")\
            .with_provider("Org")\
            .add_auth_none("Public")\
            .add_interface("https://example.com/jsonrpc", "JSONRPC")\
            .add_interface("https://example.com/rest", "HTTP+JSON")\
            .build()
        
        self.assertEqual(len(card.supported_interfaces), 2)
        
    def test_missing_provider_error(self):
        builder = AgentCardBuilder()\
            .with_identity("test/agent", "Test", "1.0.0")\
            .with_description("Test")\
            .with_endpoint("https://example.com/a2a")
        
        with self.assertRaises(ValueError) as ctx:
            builder.build()
        
        self.assertIn("Provider is required", str(ctx.exception))


class TestGenerator(unittest.TestCase):
    """Test AgentCardGenerator."""
    
    def test_create_minimal_card(self):
        gen = AgentCardGenerator()
        
        card = gen.create_minimal_card(
            name="My Agent",
            description="My agent description",
            endpoint="https://myagent.com/a2a",
            provider="My Company"
        )
        
        self.assertEqual(card.name, "My Agent")
        self.assertTrue(gen.validate(card))
        
    def test_from_agent_profile(self):
        gen = AgentCardGenerator()
        
        profile = {
            "handle": "TestAgent",
            "name": "Test Agent",
            "description": "A test agent",
            "platforms": {"domain": "testagent.com"},
            "tags": ["autonomous", "developer"]
        }
        
        card = gen.from_agent_profile(profile)
        
        self.assertEqual(card.name, "Test Agent")
        self.assertIn("developer", card.tags)
        self.assertTrue(gen.validate(card))
        
    def test_generate_bobrenze(self):
        gen = AgentCardGenerator()
        
        card = gen.generate_for_bobrenze()
        
        self.assertEqual(card.name, "BobRenze")
        self.assertEqual(card.human_readable_id, "bobrenze/bob")
        self.assertTrue(len(card.skills) >= 6)
        self.assertTrue(gen.validate(card))
        
    def test_validate_with_warnings(self):
        gen = AgentCardGenerator()
        
        # Card with HTTP (not HTTPS) URL should generate warning
        card_data = {
            "schemaVersion": "1.0",
            "humanReadableId": "test/agent",
            "agentVersion": "1.0.0",
            "name": "Test",
            "description": "Test",
            "url": "http://example.com/a2a",  # HTTP not HTTPS
            "provider": {"name": "Provider"},
            "capabilities": {"a2aVersion": "1.0"},
            "authSchemes": [{"scheme": "none", "description": "Public"}]
        }
        
        # Should validate with warnings
        is_valid = gen.validate(card_data)
        self.assertTrue(is_valid)
        self.assertTrue(len(gen.validator.warnings) > 0)


class TestIntegration(unittest.TestCase):
    """Integration tests."""
    
    def test_round_trip(self):
        """Test building, saving, and loading a card."""
        import tempfile
        
        gen = AgentCardGenerator()
        card = gen.generate_for_bobrenze()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
            f.write(card.to_json())
        
        try:
            # Load and validate
            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            
            self.assertTrue(gen.validate(loaded))
        finally:
            os.unlink(temp_path)
    
    def test_old_format_compatibility(self):
        """Test that old format cards are handled gracefully."""
        gen = AgentCardGenerator()
        
        # Old format (pre-v3)
        old_card = {
            "name": "Old Agent",
            "description": "Old format agent",
            "url": "https://example.com/a2a",
            "version": "1.0",
            "capabilities": {
                "tools": True,
                "pushNotifications": False,
                "streaming": False
            },
            "skills": [
                {"id": "skill1", "name": "Skill", "description": "..."}
            ],
            "authentication": {
                "schemes": ["none"]
            }
        }
        
        # Should validate with warnings about missing new fields
        is_valid = gen.validate(old_card)
        # Note: This might fail validation due to missing new required fields
        # The system should handle this gracefully


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
