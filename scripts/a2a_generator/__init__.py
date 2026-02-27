"""
AgentFolio Agent Card Generation Module

Refactored A2A agent-card.json generation logic.

Exports:
    AgentCardGenerator: Main class for generating and validating agent cards
    AgentCardBuilder: Fluent builder for constructing agent cards
    AgentCard: Agent card data class
    AgentCardValidator: Validation utility
    Provider, Capability, AuthScheme, Skill, SupportedInterface: Component classes
"""

from .generate_agent_card import (
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

__version__ = "3.0.0"
__all__ = [
    "AgentCardGenerator",
    "AgentCardBuilder", 
    "AgentCardValidator",
    "AgentCard",
    "Provider",
    "Capability",
    "AuthScheme",
    "Skill",
    "SupportedInterface"
]
