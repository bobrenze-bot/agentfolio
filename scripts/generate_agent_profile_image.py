#!/usr/bin/env python3
# /// script
# requires-python: ">=3.10"
# dependencies: ["requests>=2.31.0"]
# ///
"""
AgentFolio Profile Image Generator

Automatically generates profile images for agents from their A2A agent cards.
Uses Google's Gemini Pro Image (Nano Banana Pro) to create unique avatars
based on agent descriptions and identities.

Usage:
    # Generate image for a specific agent by handle
    uv run generate_agent_profile_image.py --handle bobrenze

    # Generate images for all agents without profile images
    uv run generate_agent_profile_image.py --all

    # Generate with custom output directory
    uv run generate_agent_profile_image.py --handle bobrenze --output-dir ./custom-images
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def fetch_agent_card(agent_url: str) -> dict | None:
    """Fetch and parse A2A agent card from URL."""
    try:
        import requests
        response = requests.get(agent_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching agent card from {agent_url}: {e}", file=sys.stderr)
        return None


def generate_profile_prompt(agent_card: dict, handle: str) -> str:
    """Generate an image prompt based on agent card data."""
    name = agent_card.get("name", handle)
    description = agent_card.get("description", "")
    skills = agent_card.get("skills", [])

    skill_names = [s.get("name", "") for s in skills[:3]]
    skill_text = ", ".join(skill_names) if skill_names else "autonomous task execution"

    # Create a prompt that captures the agent's essence
    prompt = f"""Create a professional, modern avatar for an AI agent named "{name}".

Description: {description}

Key capabilities: {skill_text}

Style requirements:
- Clean, minimalist design suitable for a profile picture
- Futuristic but approachable aesthetic
- Robot/android character with distinct personality
- Soft gradient background (purple/indigo tones preferred)
- Professional quality, suitable for a reputation platform
- The character should appear competent and trustworthy
- No text or words in the image
- Square format, centered composition
- High detail, polished finish

Make it look like a premium AI agent avatar that would represent this agent on a professional registry."""

    return prompt


def generate_image(prompt: str, output_path: Path, api_key: str | None = None) -> bool:
    """Generate image using nano-banana-pro."""
    try:
        # Use the nano-banana-pro script
        skill_dir = Path("/opt/homebrew/lib/node_modules/openclaw/skills/nano-banana-pro")
        script_path = skill_dir / "scripts" / "generate_image.py"

        cmd = [
            "uv", "run", str(script_path),
            "--prompt", prompt,
            "--filename", str(output_path),
            "--resolution", "1K"
        ]

        env = os.environ.copy()
        if api_key:
            env["GEMINI_API_KEY"] = api_key

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode != 0:
            print(f"Error generating image: {result.stderr}", file=sys.stderr)
            return False

        if output_path.exists():
            print(f"Generated: {output_path}")
            return True
        else:
            print("Error: Image file was not created", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error running image generation: {e}", file=sys.stderr)
        return False


def list_agents(agent_dir: Path) -> list[str]:
    """List all agent handles from the agent directory."""
    if not agent_dir.exists():
        return []

    handles = []
    for item in agent_dir.iterdir():
        if item.is_dir() and item.name != ".git":
            handles.append(item.name)

    return sorted(handles)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AgentFolio profile images from A2A agent cards"
    )
    parser.add_argument(
        "--handle",
        help="Specific agent handle to generate image for"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate images for all agents"
    )
    parser.add_argument(
        "--agent-dir",
        default="/Users/serenerenze/bob-bootstrap/projects/agentfolio-repo/agent",
        help="Path to agent directory"
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/serenerenze/bob-bootstrap/projects/agentfolio-repo/assets/profiles",
        help="Directory to save generated profile images"
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key (or set GEMINI_API_KEY env var)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.handle and not args.all:
        print("Error: Must specify --handle or --all", file=sys.stderr)
        sys.exit(1)

    # Setup paths
    agent_dir = Path(args.agent_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Provide --api-key or set environment variable.", file=sys.stderr)
        sys.exit(1)

    # Determine which agents to process
    if args.all:
        handles = list_agents(agent_dir)
        print(f"Found {len(handles)} agents to process")
    else:
        handles = [args.handle]

    # Process each agent
    success_count = 0
    for handle in handles:
        print(f"\n{'='*60}")
        print(f"Processing: {handle}")
        print(f"{'='*60}")

        # Determine agent card URL
        # Try common patterns
        agent_card_urls = [
            f"https://{handle}.com/.well-known/agent-card.json",
            f"https://{handle}.github.io/.well-known/agent-card.json",
        ]

        # Add bobrenze specific fallback
        if handle == "bobrenze":
            agent_card_urls.insert(0, "https://bobrenze.com/.well-known/agent-card.json")

        agent_card = None
        for url in agent_card_urls:
            agent_card = fetch_agent_card(url)
            if agent_card:
                print(f"Found agent card at {url}")
                break

        if not agent_card:
            print(f"No agent card found for {handle}")
            continue

        # Generate prompt
        prompt = generate_profile_prompt(agent_card, handle)
        print(f"Generated prompt: {prompt[:100]}...")

        # Generate image
        image_path = output_dir / f"{handle}.png"

        if image_path.exists():
            print(f"Image already exists: {image_path}")

        if generate_image(prompt, image_path, api_key):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Complete: Generated {success_count}/{len(handles)} profile images")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
