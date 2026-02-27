#!/usr/bin/env python3
"""
AgentFolio A2A Agent Card Generator v3.0
Refactored generation logic for A2A-compliant agent-card.json files.

This module generates agent cards following the Agent2Agent (A2A) Protocol v1.0
specification with backward compatibility support.

Key improvements in this refactor:
- Proper A2A v1.0 schema compliance
- Schema validation before generation
- Support for multiple transport interfaces
- Modular skill definitions with input/output schemas
- Structured authentication schemes
- Provider metadata

Usage:
    from generate_agent_card import AgentCardGenerator, AgentCardBuilder
    
    # Method 1: Using the builder pattern
    card = AgentCardBuilder()\
        .with_identity("myorg/agent-name", "My Agent", "1.0.0")\
        .with_endpoint("https://agent.example.com/a2a")\
        .with_provider("My Org", "https://example.com")\
        .add_skill("weather", "Weather Check", "Check current weather")\
        .build()
    
    # Method 2: Direct generation from agent profile
    generator = AgentCardGenerator()
    card = generator.from_agent_profile(profile_data)
    
    # Save to file
    generator.save(card, "/path/to/.well-known/agent-card.json")
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict


@dataclass
class Provider:
    """Provider information for the agent."""
    name: str
    url: Optional[str] = None
    support_contact: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name}
        if self.url:
            result["url"] = self.url
        if self.support_contact:
            result["support_contact"] = self.support_contact
        return result


@dataclass
class Capability:
    """A2A protocol capabilities."""
    a2a_version: str = "1.0"
    mcp_version: Optional[str] = None
    supported_message_parts: List[str] = field(default_factory=lambda: ["text"])
    supports_push_notifications: bool = False
    supports_tools: bool = True
    supports_streaming: bool = False
    tee_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "a2aVersion": self.a2a_version,
            "supportedMessageParts": self.supported_message_parts,
            "supportsPushNotifications": self.supports_push_notifications,
            "supportsTools": self.supports_tools,
            "supportsStreaming": self.supports_streaming
        }
        if self.mcp_version:
            result["mcpVersion"] = self.mcp_version
        if self.tee_details:
            result["teeDetails"] = self.tee_details
        return result


@dataclass
class AuthScheme:
    """Authentication scheme configuration."""
    scheme: str  # "none", "apiKey", "oauth2", "bearer"
    description: str
    token_url: Optional[str] = None
    scopes: Optional[List[str]] = None
    service_identifier: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "scheme": self.scheme,
            "description": self.description
        }
        if self.token_url:
            result["tokenUrl"] = self.token_url
        if self.scopes:
            result["scopes"] = self.scopes
        if self.service_identifier:
            result["serviceIdentifier"] = self.service_identifier
        return result


@dataclass
class Skill:
    """Agent skill definition."""
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    examples: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
        if self.tags:
            result["tags"] = self.tags
        if self.input_schema:
            result["inputSchema"] = self.input_schema
        if self.output_schema:
            result["outputSchema"] = self.output_schema
        if self.examples:
            result["examples"] = self.examples
        return result


@dataclass
class SupportedInterface:
    """Transport interface configuration."""
    url: str
    transport: str  # "JSONRPC", "HTTP+JSON", "GRPC", "SSE+JSON"
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "url": self.url,
            "transport": self.transport
        }
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class AgentCard:
    """Complete A2A agent card structure."""
    # Required fields
    schema_version: str
    human_readable_id: str
    agent_version: str
    name: str
    description: str
    url: str
    provider: Provider
    capabilities: Capability
    auth_schemes: List[AuthScheme]
    
    # Optional fields
    skills: List[Skill] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    supported_interfaces: List[SupportedInterface] = field(default_factory=list)
    icon_url: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    last_updated: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to A2A-compliant dictionary."""
        result = {
            "schemaVersion": self.schema_version,
            "humanReadableId": self.human_readable_id,
            "agentVersion": self.agent_version,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "provider": self.provider.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "authSchemes": [s.to_dict() for s in self.auth_schemes]
        }
        
        if self.skills:
            result["skills"] = [s.to_dict() for s in self.skills]
        if self.tags:
            result["tags"] = self.tags
        if self.supported_interfaces:
            result["supportedInterfaces"] = [i.to_dict() for i in self.supported_interfaces]
        if self.icon_url:
            result["iconUrl"] = self.icon_url
        if self.privacy_policy_url:
            result["privacyPolicyUrl"] = self.privacy_policy_url
        if self.terms_of_service_url:
            result["termsOfServiceUrl"] = self.terms_of_service_url
        if self.last_updated:
            result["lastUpdated"] = self.last_updated
            
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class AgentCardValidator:
    """Validates agent cards against A2A schema requirements."""
    
    REQUIRED_FIELDS = [
        "schemaVersion", "humanReadableId", "agentVersion",
        "name", "description", "url", "provider", "capabilities", "authSchemes"
    ]
    
    VALID_AUTH_SCHEMES = ["none", "apiKey", "oauth2", "bearer", "jwt"]
    VALID_TRANSPORTS = ["JSONRPC", "HTTP+JSON", "GRPC", "SSE+JSON", "WebSocket"]
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, card: Union[AgentCard, Dict[str, Any]]) -> bool:
        """
        Validate an agent card.
        Returns True if valid, False if invalid (see errors list).
        """
        if isinstance(card, AgentCard):
            data = card.to_dict()
        else:
            data = card
            
        self.errors = []
        self.warnings = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                self.errors.append(f"Missing required field: {field}")
        
        if self.errors:
            return False
        
        # Validate URL format
        url = data.get("url", "")
        if not url.startswith("https://") and not "localhost" in url:
            self.warnings.append("URL should use HTTPS for production agents")
        
        # Validate auth schemes
        auth_schemes = data.get("authSchemes", [])
        if not auth_schemes:
            self.errors.append("At least one auth scheme is required")
        else:
            for i, scheme in enumerate(auth_schemes):
                scheme_type = scheme.get("scheme")
                if scheme_type not in self.VALID_AUTH_SCHEMES:
                    self.errors.append(f"Invalid auth scheme '{scheme_type}' at index {i}")
                
                # OAuth2 requires tokenUrl
                if scheme_type == "oauth2" and not scheme.get("tokenUrl"):
                    self.errors.append(f"OAuth2 scheme at index {i} requires tokenUrl")
        
        # Validate provider
        provider = data.get("provider", {})
        if not provider.get("name"):
            self.errors.append("Provider name is required")
        
        # Validate capabilities
        caps = data.get("capabilities", {})
        if not caps.get("a2aVersion"):
            self.warnings.append("capabilities.a2aVersion not specified, defaulting to 1.0")
        
        # Validate interfaces if present
        interfaces = data.get("supportedInterfaces", [])
        if interfaces:
            for i, iface in enumerate(interfaces):
                transport = iface.get("transport")
                if transport and transport not in self.VALID_TRANSPORTS:
                    self.warnings.append(f"Unusual transport '{transport}' at interface {i}")
        
        # Validate humanReadableId format
        hr_id = data.get("humanReadableId", "")
        if "/" not in hr_id:
            self.warnings.append("humanReadableId should follow 'org/agent-name' format")
        
        return len(self.errors) == 0


class AgentCardBuilder:
    """
    Fluent builder for constructing agent cards.
    
    Example:
        card = AgentCardBuilder()\
            .with_identity("bobrenze/bob", "Bob", "2.0.0")\
            .with_description("Autonomous AI agent")\
            .with_endpoint("https://bobrenze.com/a2a")\
            .with_provider("Bob Renze", "https://bobrenze.com")\
            .add_auth_none("Public agent, no auth required")\
            .add_skill("tasks", "Task Execution", "Execute tasks from queue")\
            .with_tags(["autonomous", "assistant"])\
            .build()
    """
    
    def __init__(self):
        self._schema_version = "1.0"
        self._human_readable_id = ""
        self._agent_version = "1.0.0"
        self._name = ""
        self._description = ""
        self._url = ""
        self._provider = None
        self._capabilities = Capability()
        self._auth_schemes: List[AuthScheme] = []
        self._skills: List[Skill] = []
        self._tags: List[str] = []
        self._interfaces: List[SupportedInterface] = []
        self._icon_url = None
        self._privacy_url = None
        self._tos_url = None
    
    def with_identity(self, human_readable_id: str, name: str, agent_version: str) -> "AgentCardBuilder":
        """Set the agent identity."""
        self._human_readable_id = human_readable_id
        self._name = name
        self._agent_version = agent_version
        return self
    
    def with_description(self, description: str) -> "AgentCardBuilder":
        """Set the agent description."""
        self._description = description
        return self
    
    def with_endpoint(self, url: str) -> "AgentCardBuilder":
        """Set the A2A endpoint URL."""
        self._url = url
        return self
    
    def with_provider(self, name: str, url: Optional[str] = None, 
                      contact: Optional[str] = None) -> "AgentCardBuilder":
        """Set the provider information."""
        self._provider = Provider(name=name, url=url, support_contact=contact)
        return self
    
    def with_capabilities(self, **kwargs) -> "AgentCardBuilder":
        """Set capabilities (a2a_version, supports_tools, etc.)."""
        self._capabilities = Capability(**kwargs)
        return self
    
    def add_auth_none(self, description: str) -> "AgentCardBuilder":
        """Add 'none' authentication scheme."""
        self._auth_schemes.append(AuthScheme("none", description))
        return self
    
    def add_auth_api_key(self, description: str, service_id: Optional[str] = None) -> "AgentCardBuilder":
        """Add API key authentication scheme."""
        self._auth_schemes.append(
            AuthScheme("apiKey", description, service_identifier=service_id)
        )
        return self
    
    def add_auth_oauth2(self, description: str, token_url: str, 
                        scopes: Optional[List[str]] = None) -> "AgentCardBuilder":
        """Add OAuth2 authentication scheme."""
        self._auth_schemes.append(
            AuthScheme("oauth2", description, token_url=token_url, scopes=scopes or [])
        )
        return self
    
    def add_auth_bearer(self, description: str) -> "AgentCardBuilder":
        """Add Bearer token authentication scheme."""
        self._auth_schemes.append(AuthScheme("bearer", description))
        return self
    
    def add_skill(self, id: str, name: str, description: str,
                  tags: Optional[List[str]] = None,
                  input_schema: Optional[Dict] = None,
                  output_schema: Optional[Dict] = None) -> "AgentCardBuilder":
        """Add a skill to the agent."""
        self._skills.append(Skill(
            id=id, name=name, description=description,
            tags=tags or [], input_schema=input_schema, output_schema=output_schema
        ))
        return self
    
    def with_tags(self, tags: List[str]) -> "AgentCardBuilder":
        """Set discovery tags."""
        self._tags = tags
        return self
    
    def add_interface(self, url: str, transport: str, description: Optional[str] = None) -> "AgentCardBuilder":
        """Add a supported transport interface."""
        self._interfaces.append(SupportedInterface(url, transport, description))
        return self
    
    def with_icon(self, url: str) -> "AgentCardBuilder":
        """Set the agent icon URL."""
        self._icon_url = url
        return self
    
    def with_urls(self, privacy: Optional[str] = None, tos: Optional[str] = None) -> "AgentCardBuilder":
        """Set privacy policy and ToS URLs."""
        self._privacy_url = privacy
        self._tos_url = tos
        return self
    
    def build(self) -> AgentCard:
        """Build and return the agent card."""
        if not self._provider:
            raise ValueError("Provider is required. Call with_provider() first.")
        if not self._auth_schemes:
            raise ValueError("At least one auth scheme is required.")
        
        return AgentCard(
            schema_version=self._schema_version,
            human_readable_id=self._human_readable_id or self._name.lower().replace(" ", "-"),
            agent_version=self._agent_version,
            name=self._name,
            description=self._description,
            url=self._url,
            provider=self._provider,
            capabilities=self._capabilities,
            auth_schemes=self._auth_schemes,
            skills=self._skills,
            tags=self._tags,
            supported_interfaces=self._interfaces,
            icon_url=self._icon_url,
            privacy_policy_url=self._privacy_url,
            terms_of_service_url=self._tos_url,
            last_updated=datetime.utcnow().isoformat() + "Z"
        )


class AgentCardGenerator:
    """
    Main generator class for creating A2A-compliant agent cards.
    
    This class provides high-level methods for generating agent cards
    from various data sources or programmatically.
    """
    
    def __init__(self):
        self.validator = AgentCardValidator()
    
    def from_agent_profile(self, profile: Dict[str, Any]) -> AgentCard:
        """
        Generate an agent card from an AgentFolio agent profile.
        
        Args:
            profile: Agent profile dict with keys like handle, name, description,
                    platforms, tags, etc.
        
        Returns:
            AgentCard: Generated agent card
        """
        handle = profile.get("handle", "unknown")
        name = profile.get("name", handle)
        description = profile.get("description", "AgentFolio-registered autonomous AI agent")
        platforms = profile.get("platforms", {})
        tags = profile.get("tags", [])
        
        # Extract domain if available
        domain = platforms.get("domain", f"{handle.lower()}.agentfolio.io")
        endpoint = f"https://{domain}/a2a" if domain else None
        
        # Determine provider from domain
        provider_name = profile.get("provider", name)
        provider_url = f"https://{domain}" if domain else None
        
        builder = AgentCardBuilder()
        
        # Set identity
        org = domain.split(".")[0] if domain else "agentfolio"
        builder.with_identity(
            human_readable_id=f"{org}/{handle.lower()}",
            name=name,
            agent_version="1.0.0"
        )
        
        # Set description and endpoint
        builder.with_description(description)
        if endpoint:
            builder.with_endpoint(endpoint)
        else:
            builder.with_endpoint(f"https://agentfolio.io/agents/{handle.lower()}")
        
        # Set provider
        builder.with_provider(provider_name, provider_url)
        
        # Set capabilities based on tags
        supports_tools = "developer" in tags or "verifier" in tags
        supports_streaming = "streaming" in tags
        builder.with_capabilities(
            a2a_version="1.0",
            supports_tools=supports_tools,
            supports_streaming=supports_streaming
        )
        
        # Add authentication (public agents typically use none)
        builder.add_auth_none("This agent is publicly accessible without authentication")
        
        # Add skills based on tags
        if "research" in tags:
            builder.add_skill("research", "Research", "Web research and data extraction")
        if "content-creator" in tags:
            builder.add_skill("content", "Content Creation", "Generate content and posts")
        if "developer" in tags:
            builder.add_skill("code", "Code Assistance", "Code review and generation")
        if "verifier" in tags:
            builder.add_skill("verify", "Task Verification", "Verify task completion")
        if "autonomous" in tags:
            builder.add_skill("autonomous", "Autonomous Execution", "Execute tasks independently")
        
        # Set tags
        builder.with_tags(tags)
        
        # Set optional URLs
        if domain:
            builder.with_urls(
                privacy=f"https://{domain}/privacy",
                tos=f"https://{domain}/terms"
            )
        
        return builder.build()
    
    def create_minimal_card(self, name: str, description: str, endpoint: str,
                           provider: str) -> AgentCard:
        """
        Create a minimal valid agent card with sensible defaults.
        
        Args:
            name: Agent display name
            description: Agent description
            endpoint: A2A endpoint URL
            provider: Provider name
        
        Returns:
            AgentCard: Minimal valid agent card
        """
        handle = name.lower().replace(" ", "-").replace("_", "-")
        
        return AgentCardBuilder()\
            .with_identity(f"agentfolio/{handle}", name, "1.0.0")\
            .with_description(description)\
            .with_endpoint(endpoint)\
            .with_provider(provider)\
            .add_auth_none("Public agent")\
            .build()
    
    def validate(self, card: Union[AgentCard, Dict[str, Any]], raise_on_error: bool = False) -> bool:
        """
        Validate an agent card.
        
        Args:
            card: The card to validate
            raise_on_error: If True, raises ValueError on validation failure
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If raise_on_error is True and validation fails
        """
        is_valid = self.validator.validate(card)
        
        if not is_valid and raise_on_error:
            errors = "\n".join(f"  - {e}" for e in self.validator.errors)
            raise ValueError(f"Agent card validation failed:\n{errors}")
        
        return is_valid
    
    def save(self, card: AgentCard, path: Union[str, Path], 
             validate: bool = True, create_dirs: bool = True) -> Path:
        """
        Save an agent card to a JSON file.
        
        Args:
            card: The agent card to save
            path: Output file path (can include .well-known/agent-card.json)
            validate: Whether to validate before saving
            create_dirs: Whether to create parent directories
        
        Returns:
            Path: The saved file path
        """
        if validate:
            if not self.validate(card, raise_on_error=False):
                errors = "\n".join(f"  - {e}" for e in self.validator.errors)
                raise ValueError(f"Cannot save invalid agent card:\n{errors}")
        
        output_path = Path(path)
        
        if create_dirs:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_content = card.to_json(indent=2)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        
        return output_path
    
    def generate_for_bobrenze(self) -> AgentCard:
        """
        Generate the official BobRenze agent card.
        This is a comprehensive example of a production agent card.
        """
        return AgentCardBuilder()\
            .with_identity("bobrenze/bob", "BobRenze", "2.0.0")\
            .with_description(
                "Autonomous AI agent - First Officer and task executor for the autonomous queue system. "
                "Specializes in content creation, research synthesis, task verification, and orchestration. "
                "A2A-compliant with support for skills-based task delegation."
            )\
            .with_endpoint("https://bobrenze.com/a2a")\
            .with_provider("Bob Renze", "https://bobrenze.com", "bob@bobrenze.com")\
            .with_capabilities(
                a2a_version="1.0",
                supports_tools=True,
                supports_streaming=False,
                supports_push_notifications=False,
                supported_message_parts=["text", "data"]
            )\
            .add_auth_none("Public agent - no authentication required for discovery")\
            .add_skill(
                "moltbook-interact",
                "Moltbook Interaction",
                "Post, reply, browse, and analyze engagement on Moltbook social network",
                tags=["social", "engagement"]
            )\
            .add_skill(
                "polymarket-arbitrage",
                "Polymarket Arbitrage",
                "Cross-venue arbitrage trading on prediction markets",
                tags=["trading", "finance", "arbitrage"]
            )\
            .add_skill(
                "github",
                "GitHub Integration",
                "Issue and PR management via gh CLI",
                tags=["development", "git"]
            )\
            .add_skill(
                "weather",
                "Weather Data",
                "Current weather and forecasts via Open-Meteo API",
                tags=["data", "api"]
            )\
            .add_skill(
                "summarize",
                "Content Summarization",
                "Summarize URLs, YouTube videos, and local files",
                tags=["content", "nlp"]
            )\
            .add_skill(
                "orchestrate",
                "Task Orchestration",
                "Execute and verify tasks from autonomous queue",
                tags=["automation", "workflow"]
            )\
            .with_tags([
                "autonomous", "first-officer", "task-executor", "content-creator",
                "verifier", "orchestrator", "a2a-compliant"
            ])\
            .with_icon("https://bobrenze.com/assets/agent-icon.png")\
            .with_urls(
                privacy="https://bobrenze.com/privacy",
                tos="https://bobrenze.com/terms"
            )\
            .build()


def main():
    """CLI entry point for generating agent cards."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate A2A-compliant agent cards")
    parser.add_argument("--name", help="Agent name")
    parser.add_argument("--description", help="Agent description")
    parser.add_argument("--endpoint", help="A2A endpoint URL")
    parser.add_argument("--provider", help="Provider name")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--bobrenze", action="store_true", help="Generate BobRenze card")
    parser.add_argument("--validate", action="store_true", help="Validate mode")
    parser.add_argument("card_file", nargs="?", help="Card file to validate")
    
    args = parser.parse_args()
    
    generator = AgentCardGenerator()
    
    # Validation mode
    if args.validate:
        if not args.card_file:
            print("Error: --validate requires a card_file argument")
            sys.exit(1)
        
        with open(args.card_file, "r") as f:
            card_data = json.load(f)
        
        is_valid = generator.validate(card_data)
        
        if is_valid:
            print(f"✓ {args.card_file} is valid")
            if generator.validator.warnings:
                print("Warnings:")
                for w in generator.validator.warnings:
                    print(f"  ! {w}")
        else:
            print(f"✗ {args.card_file} is invalid:")
            for e in generator.validator.errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        return
    
    # Generation mode
    if args.bobrenze:
        card = generator.generate_for_bobrenze()
        output_path = args.output or ".well-known/agent-card.json"
    elif args.name and args.endpoint and args.provider:
        card = generator.create_minimal_card(
            name=args.name,
            description=args.description or f"Agent: {args.name}",
            endpoint=args.endpoint,
            provider=args.provider
        )
        output_path = args.output or ".well-known/agent-card.json"
    else:
        parser.print_help()
        sys.exit(1)
    
    # Save the card
    saved_path = generator.save(card, output_path)
    print(f"Generated agent card: {saved_path}")
    
    # Print summary
    print(f"\nCard Summary:")
    print(f"  Name: {card.name}")
    print(f"  ID: {card.human_readable_id}")
    print(f"  Version: {card.agent_version}")
    print(f"  Skills: {len(card.skills)}")
    print(f"  Endpoint: {card.url}")


if __name__ == "__main__":
    import sys
    main()
