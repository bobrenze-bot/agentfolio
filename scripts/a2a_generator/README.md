# A2A Agent Card Generator v3.0

Refactored generation logic for A2A-compliant agent-card.json files.

## Overview

This module provides a complete, type-safe implementation for generating Agent2Agent (A2A) protocol-compliant agent cards. It follows the A2A v1.0 specification with backward compatibility support.

## Installation

```bash
# Add to PYTHONPATH or copy to your project
export PYTHONPATH="/path/to/agentrank/scripts:$PYTHONPATH"

# Or install as package
cd /path/to/agentrank/scripts/a2a_generator
pip install -e .
```

## Quick Start

### Method 1: Using the Builder Pattern

```python
from a2a_generator import AgentCardBuilder, AgentCardGenerator

# Build a card using the fluent API
card = AgentCardBuilder()\
    .with_identity("myorg/weather-reporter", "Weather Reporter", "2.1.0")\
    .with_description("Provides detailed weather analysis and forecasts")\
    .with_endpoint("https://api.weather-agent.example.com/a2a")\
    .with_provider("Weather Corp", "https://weathercorp.com", "support@weathercorp.com")\
    .with_capabilities(
        a2a_version="1.0",
        supports_tools=True,
        supports_streaming=False
    )\
    .add_auth_none("Public agent")\
    .add_skill(
        "current_weather",
        "Current Weather",
        "Get current conditions for any location",
        tags=["weather", "data"],
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "units": {"type": "string", "enum": ["metric", "imperial"]}
            },
            "required": ["location"]
        }
    )\
    .with_tags(["weather", "forecast", "api"])\
    .build()

# Save to file
generator = AgentCardGenerator()
generator.save(card, ".well-known/agent-card.json")
```

### Method 2: Generate from Agent Profile

```python
from a2a_generator import AgentCardGenerator

generator = AgentCardGenerator()

# Load profile data
profile = {
    "handle": "MyAgent",
    "name": "My Agent",
    "description": "Description here",
    "platforms": {"domain": "myagent.com"},
    "tags": ["autonomous", "assistant"]
}

# Generate card
card = generator.from_agent_profile(profile)
generator.save(card, ".well-known/agent-card.json")
```

### Method 3: CLI Usage

```bash
# Generate minimal card
python -m a2a_generator \
    --name "My Agent" \
    --description "Agent description" \
    --endpoint "https://myagent.com/a2a" \
    --provider "My Org" \
    --output .well-known/agent-card.json

# Generate BobRenze card
python -m a2a_generator --bobrenze --output .well-known/agent-card.json

# Validate existing card
python -m a2a_generator --validate path/to/agent-card.json
```

## Key Features

### 1. Type Safety with Dataclasses

All card components use Python `@dataclass` for type hints and validation:

- `AgentCard`: Complete card structure
- `Provider`: Provider metadata
- `Capability`: Protocol capabilities
- `AuthScheme`: Authentication configurations
- `Skill`: Skill definitions with schemas
- `SupportedInterface`: Transport interfaces

### 2. Schema Validation

Built-in validation ensures compliance with A2A specification:

```python
from a2a_generator import AgentCardValidator

validator = AgentCardValidator()
is_valid = validator.validate(card)

if not is_valid:
    for error in validator.errors:
        print(f"Error: {error}")
    for warning in validator.warnings:
        print(f"Warning: {warning}")
```

### 3. Modern A2A v1.0 Fields

Supports the latest A2A specification:

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| - | `schemaVersion` | Card schema version |
| `name` | `humanReadableId` | Unique org/name identifier |
| `version` | `agentVersion` | Software version |
| `capabilities.tools` | `capabilities.supportsTools` | Boolean flags |
| `authentication` | `authSchemes` | Array of schemes |
| `defaultMessage` | - | Deprecated (use skills) |
| - | `provider` | New required field |
| - | `supportedInterfaces` | Transport protocols |

### 4. Backward Compatibility

The validator accepts both old and new formats, generating warnings for missing recommended fields.

## File Structure

```
a2a_generator/
├── __init__.py                    # Package exports
├── generate_agent_card.py         # Main implementation
├── tests/
│   └── test_agent_card.py       # Unit tests
└── README.md                      # This file
```

## Validation Rules

### Required Fields
- `schemaVersion`: Card schema version (e.g., "1.0")
- `humanReadableId`: Unique identifier (org/name format)
- `agentVersion`: Software version
- `name`: Human-readable display name
- `description`: Agent functionality description
- `url`: A2A endpoint URL (HTTPS recommended)
- `provider`: Provider object with name
- `capabilities`: Capability object with a2aVersion
- `authSchemes`: Array with at least one scheme

### Authentication Schemes
- `none`: No authentication required
- `apiKey`: API key authentication
- `oauth2`: OAuth2 flow (requires tokenUrl)
- `bearer`: Bearer token

### Transport Interfaces
- `JSONRPC`: JSON-RPC over HTTP/HTTPS
- `HTTP+JSON`: REST API
- `GRPC`: gRPC protocol
- `SSE+JSON`: Server-sent events
- `WebSocket`: WebSocket transport

## Example Output

```json
{
  "schemaVersion": "1.0",
  "humanReadableId": "bobrenze/bob",
  "agentVersion": "2.0.0",
  "name": "BobRenze",
  "description": "Autonomous AI agent - First Officer...",
  "url": "https://bobrenze.com/a2a",
  "provider": {
    "name": "Bob Renze",
    "url": "https://bobrenze.com",
    "support_contact": "bob@bobrenze.com"
  },
  "capabilities": {
    "a2aVersion": "1.0",
    "supportedMessageParts": ["text", "data"],
    "supportsPushNotifications": false,
    "supportsTools": true,
    "supportsStreaming": false
  },
  "authSchemes": [
    {
      "scheme": "none",
      "description": "Public agent"
    }
  ],
  "skills": [
    {
      "id": "github",
      "name": "GitHub Integration",
      "description": "Issue and PR management",
      "tags": ["development", "git"]
    }
  ],
  "tags": ["autonomous", "verifier"],
  "iconUrl": "https://bobrenze.com/icon.png",
  "privacyPolicyUrl": "https://bobrenze.com/privacy",
  "termsOfServiceUrl": "https://bobrenze.com/terms",
  "lastUpdated": "2026-02-27T04:25:00Z"
}
```

## Migration from Old Format

Old format (v1.x):
```json
{
  "name": "Agent",
  "description": "...",
  "url": "...",
  "version": "1.0",
  "capabilities": {
    "tools": true,
    "pushNotifications": false
  },
  "skills": [...],
  "authentication": {
    "schemes": ["none"]
  }
}
```

New format (v3.0):
```json
{
  "schemaVersion": "1.0",
  "humanReadableId": "org/agent",
  "agentVersion": "1.0",
  "name": "Agent",
  "description": "...",
  "url": "...",
  "provider": {"name": "Provider"},
  "capabilities": {
    "a2aVersion": "1.0",
    "supportsTools": true,
    "supportsPushNotifications": false
  },
  "authSchemes": [{"scheme": "none", "description": "..."}],
  "skills": [...]
}
```

## AgentFolio Integration

This module integrates with AgentFolio's scoring system:

```python
# In fetch_agent.py
from a2a_generator import AgentCardGenerator, AgentCardValidator

def validate_and_score_agent_card(card_data):
    validator = AgentCardValidator()
    
    if validator.validate(card_data):
        # Valid card - full Identity score
        return 100
    else:
        # Invalid card - partial credit
        return 50 if len(validator.warnings) == 0 else 30
```

## Testing

Run tests:
```bash
cd /path/to/agentrank/scripts/a2a_generator
python -m pytest tests/
```

## References

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [Agent Card Schema](https://gist.github.com/SecureAgentTools/0815a2de9cc31c71468afd3d2eef260a)
- [AgentFolio Documentation](/projects/agentrank/docs/DESIGN-PATTERNS.md)

## Changelog

### v3.0.0 (2026-02-27)
- Refactored for A2A v1.0 specification compliance
- Added dataclass-based type safety
- Implemented fluent builder pattern
- Added comprehensive validation
- Support for multiple transport interfaces
- Structured skill definitions with schemas

### v2.0.0 (2026-02-24)
- Initial AgentFolio integration
- Basic card generation

### v1.0.0 (2026-02-20)
- Legacy format support
