#!/usr/bin/env python3
"""
Generate /tool/[handle]/index.html pages for AgentFolio tools & platforms.
Each page has: description, best-for, human use cases, agent use cases, install/links.
"""

import os
import json

TOOLS = {
    "crewai": {
        "name": "CrewAI",
        "emoji": "🚢",
        "category": "Agent Framework",
        "tagline": "Role-based multi-agent orchestration",
        "description": "CrewAI is a Python framework for building multi-agent systems where each agent has a defined role, goal, and backstory. Agents collaborate like a crew — a researcher finds information, a writer drafts content, an editor reviews it. Optimized for deliberate, structured workflows.",
        "best_for": "Multi-step workflows where different agents need different specializations. Great for content pipelines, research-and-write tasks, and sequential task chains.",
        "human_uses": [
            "Build a content pipeline: researcher + writer + editor agents",
            "Automate business workflows with role-specific AI workers",
            "Create customer service systems with triage + specialist agents",
            "Research automation with specialized data-gathering agents"
        ],
        "agent_uses": [
            "Delegate subtasks to specialist sub-agents with defined roles",
            "Orchestrate parallel research streams with a coordinator agent",
            "Build verification pipelines (executor → reviewer → approver)",
            "Implement multi-stage data processing with typed handoffs"
        ],
        "install": "pip install crewai",
        "quick_start": "from crewai import Agent, Task, Crew\nagent = Agent(role='Researcher', goal='Find facts', backstory='Expert researcher')\ntask = Task(description='Research AI agents', agent=agent)\ncrew = Crew(agents=[agent], tasks=[task])\nresult = crew.kickoff()",
        "links": {
            "Website": "https://crewai.com",
            "GitHub": "https://github.com/joaomdmoura/crewAI",
            "Docs": "https://docs.crewai.com",
            "PyPI": "https://pypi.org/project/crewai"
        }
    },
    "langgraph": {
        "name": "LangGraph",
        "emoji": "🕸️",
        "category": "Agent Framework",
        "tagline": "Graph-based stateful agent workflows",
        "description": "LangGraph builds on LangChain to let you define agent workflows as directed graphs with explicit state management. Nodes are functions or agents; edges define flow. Supports cycles, conditional branching, and human-in-the-loop checkpoints. ~2.2x faster than CrewAI in benchmarks.",
        "best_for": "Complex agent workflows requiring explicit state, conditional branching, or loops. Best for production systems where you need fine-grained control over agent behavior.",
        "human_uses": [
            "Build production-grade AI agents with explicit state machines",
            "Create chatbots with memory that can branch based on context",
            "Design multi-step reasoning systems with loops and conditions",
            "Implement human-in-the-loop approval workflows"
        ],
        "agent_uses": [
            "Define agent control flow as code rather than prompt instructions",
            "Implement reliable retry logic with graph cycles",
            "Build supervisor agents that route tasks to specialists",
            "Create auditable agent workflows with full state history"
        ],
        "install": "pip install langgraph langchain-core",
        "quick_start": "from langgraph.graph import StateGraph\nfrom typing import TypedDict\n\nclass State(TypedDict):\n    messages: list\n\ngraph = StateGraph(State)\ngraph.add_node('agent', my_agent_fn)\ngraph.set_entry_point('agent')\napp = graph.compile()",
        "links": {
            "Website": "https://langchain-ai.github.io/langgraph",
            "GitHub": "https://github.com/langchain-ai/langgraph",
            "Docs": "https://langchain-ai.github.io/langgraph/tutorials",
            "PyPI": "https://pypi.org/project/langgraph"
        }
    },
    "autogen": {
        "name": "AutoGen",
        "emoji": "🔄",
        "category": "Agent Framework",
        "tagline": "Microsoft's conversational multi-agent framework",
        "description": "AutoGen (from Microsoft Research) enables multi-agent conversations where agents can talk to each other to solve problems. Supports human-in-the-loop, code execution, and groupchat patterns. Built around the concept of agents as conversational entities.",
        "best_for": "Conversational agent systems, code generation with execution, and scenarios where agents need to debate or collaborate through dialogue.",
        "human_uses": [
            "Build coding assistants that write, run, and fix their own code",
            "Create agent teams that debate solutions before implementing",
            "Automate software engineering workflows end-to-end",
            "Build research systems where agents cross-check each other"
        ],
        "agent_uses": [
            "Implement peer review between agents before committing outputs",
            "Run sandboxed code execution to verify agent-generated scripts",
            "Build teachable agents that learn from feedback across sessions",
            "Create specialized groupchats for complex multi-domain problems"
        ],
        "install": "pip install pyautogen",
        "quick_start": "from autogen import AssistantAgent, UserProxyAgent\nassistant = AssistantAgent('assistant', llm_config={'model': 'gpt-4'})\nuser = UserProxyAgent('user', code_execution_config={'work_dir': 'coding'})\nuser.initiate_chat(assistant, message='Write a web scraper')",
        "links": {
            "Website": "https://microsoft.github.io/autogen",
            "GitHub": "https://github.com/microsoft/autogen",
            "Docs": "https://microsoft.github.io/autogen/docs/Getting-Started",
            "PyPI": "https://pypi.org/project/pyautogen"
        }
    },
    "openclaw": {
        "name": "OpenClaw",
        "emoji": "🦀",
        "category": "Agent Runtime",
        "tagline": "Personal AI agent gateway — runs 24/7 on your machine",
        "description": "OpenClaw is a local agent gateway that gives AI models persistent memory, cron scheduling, tool access (browser, exec, files, messaging), and multi-channel communication (WhatsApp, Telegram, Discord). Runs as a daemon on your machine. Your agent is always on, always accessible.",
        "best_for": "Running persistent, autonomous agents that need to act on your behalf 24/7. Connects Claude, GPT-4, or any LLM to your actual computer, calendar, messaging apps, and the web.",
        "human_uses": [
            "Personal AI assistant that persists across conversations with real memory",
            "Automated cron jobs run by your AI (send standup, check feeds, monitor inbox)",
            "Multi-channel routing: ask your agent via WhatsApp, it acts on your Mac",
            "Fleet of specialized agents (coordinator + workers) for complex workflows"
        ],
        "agent_uses": [
            "Persistent memory via file system — survives session resets",
            "Cron scheduling for autonomous background tasks",
            "Browser automation, exec, file read/write tool access",
            "Multi-agent coordination via sessions_spawn and sessions_send"
        ],
        "install": "npm install -g openclaw\nopenclaw gateway start",
        "quick_start": "# Install\nnpm install -g openclaw\n\n# Configure your agent\nopenclaw config set agent.model anthropic/claude-sonnet\n\n# Start the gateway\nopenclaw gateway start\n\n# Chat\nopenclaw chat",
        "links": {
            "Website": "https://openclaw.ai",
            "Docs": "https://docs.openclaw.ai",
            "GitHub": "https://github.com/openclaw/openclaw",
            "Discord": "https://discord.com/invite/clawd"
        }
    },
    "superagi": {
        "name": "SuperAGI",
        "emoji": "⚡",
        "category": "Agent Platform",
        "tagline": "Open-source autonomous agent infrastructure",
        "description": "SuperAGI is an open-source framework for building, running, and managing autonomous agents. Provides a GUI for agent management, supports multiple LLMs, has a marketplace of tools and templates, and includes performance telemetry.",
        "best_for": "Teams that want a managed agent platform with a visual interface. Good for non-technical users who want to run agents without writing Python.",
        "human_uses": [
            "Launch agents via web GUI without writing code",
            "Connect agents to tools: web browsing, code execution, file management",
            "Monitor agent performance with built-in telemetry dashboard",
            "Share and reuse agent templates across a team"
        ],
        "agent_uses": [
            "Run as a hosted alternative to self-managing agent infrastructure",
            "Access marketplace tools without building custom integrations",
            "Multi-agent coordination via SuperAGI's orchestration layer"
        ],
        "install": "git clone https://github.com/TransformerOptimus/SuperAGI\ncd SuperAGI\ncp config_template.yaml config.yaml\ndocker-compose up",
        "quick_start": "# Via Docker\ngit clone https://github.com/TransformerOptimus/SuperAGI\ncd SuperAGI && cp config_template.yaml config.yaml\n# Add your API keys to config.yaml\ndocker-compose up\n# Open http://localhost:3000",
        "links": {
            "Website": "https://superagi.com",
            "GitHub": "https://github.com/TransformerOptimus/SuperAGI",
            "Docs": "https://superagi.com/docs"
        }
    },
    "agentgpt": {
        "name": "AgentGPT",
        "emoji": "🤖",
        "category": "No-Code Agent Tool",
        "tagline": "Browser-based autonomous agent — no setup required",
        "description": "AgentGPT lets you assemble and run autonomous AI agents directly in your browser. Give it a name and goal, and it breaks the goal into tasks, executes them, and reports back. No code, no install.",
        "best_for": "Quickly experimenting with autonomous agent behavior without any setup. Good for demos, simple research tasks, and understanding what agents can do.",
        "human_uses": [
            "Prototype an agent workflow in minutes without any code",
            "Run simple research or content tasks autonomously",
            "Demonstrate agent capabilities to stakeholders",
            "Test goal decomposition before building a full system"
        ],
        "agent_uses": [
            "Prototype task decomposition logic before implementing in code",
            "Quick research tasks that don't require persistent memory"
        ],
        "install": "No install — runs in browser at reworkd.ai\n\n# Or self-host:\ngit clone https://github.com/reworkd/AgentGPT\ncd AgentGPT && ./setup.sh",
        "quick_start": "# No install needed\n# Visit: https://agentgpt.reworkd.ai\n# Enter goal → watch agent work",
        "links": {
            "Website": "https://agentgpt.reworkd.ai",
            "GitHub": "https://github.com/reworkd/AgentGPT"
        }
    },
    "autogpt": {
        "name": "AutoGPT",
        "emoji": "🧠",
        "category": "Agent Platform",
        "tagline": "The original autonomous agent — now a full platform",
        "description": "AutoGPT was the first widely-used autonomous agent (2023). It pioneered the idea of LLMs recursively calling themselves with tool access. Now evolved into AutoGPT Platform — a hosted service for building, running, and deploying AI agents with a visual builder.",
        "best_for": "Users who want a managed autonomous agent platform with the brand recognition of the original AutoGPT project. The platform version is more production-ready than the original open-source repo.",
        "human_uses": [
            "Run long-horizon tasks that require multiple steps and tool use",
            "Automate internet research, file management, and code tasks",
            "Use the visual builder to design agent workflows without code",
            "Deploy agents to AutoGPT's cloud hosting"
        ],
        "agent_uses": [
            "Historical reference: AutoGPT established the recursive LLM-with-tools pattern",
            "Platform API for running agents as managed services"
        ],
        "install": "# Self-hosted classic:\ngit clone https://github.com/Significant-Gravitas/AutoGPT\ncd AutoGPT && cp .env.template .env\n# Add OpenAI key to .env\npip install -r requirements.txt\npython -m autogpt",
        "quick_start": "# Or use the hosted platform:\n# Visit: https://platform.agpt.co",
        "links": {
            "Website": "https://agpt.co",
            "GitHub": "https://github.com/Significant-Gravitas/AutoGPT",
            "Platform": "https://platform.agpt.co",
            "Docs": "https://docs.agpt.co"
        }
    },
    "superagent": {
        "name": "Superagent",
        "emoji": "🦸",
        "category": "Agent Framework",
        "tagline": "API-first framework for building production AI agents",
        "description": "Superagent is an open-source framework for building and deploying production-grade AI agents via API. Supports custom tools, memory, document ingestion, and multi-LLM routing. Designed for developers who want to ship AI agents as products.",
        "best_for": "Developers building AI-powered products where agents need to be exposed as APIs. Good for adding AI agent capabilities to existing applications.",
        "human_uses": [
            "Build AI agent APIs that your frontend can call",
            "Create document Q&A systems with custom knowledge bases",
            "Add AI agent capabilities to SaaS products",
            "Build customer-facing AI assistants with tool access"
        ],
        "agent_uses": [
            "Expose agent capabilities as API endpoints for other agents to call",
            "Build specialized sub-agents accessible via HTTP",
            "Store and retrieve agent memory via the Superagent API"
        ],
        "install": "pip install superagent-py\n\n# Or use the cloud:\n# api.superagent.sh",
        "quick_start": "from superagent.client import Superagent\nclient = Superagent(token='your-token', base_url='https://api.superagent.sh')\nagent = client.agent.create(name='My Agent', llm='GPT_3_5_TURBO_16K_0613')",
        "links": {
            "Website": "https://superagent.sh",
            "GitHub": "https://github.com/superagent-ai/superagent",
            "Docs": "https://docs.superagent.sh"
        }
    },
    "e2b": {
        "name": "E2B",
        "emoji": "📦",
        "category": "Sandboxed Code Execution",
        "tagline": "Safe cloud sandboxes for AI agents to run code",
        "description": "E2B provides cloud-hosted sandboxes where AI agents can safely execute code. Each sandbox is an isolated container — agents can run Python, install packages, read/write files, and access the internet without touching the host system.",
        "best_for": "Any agent that needs to execute untrusted or AI-generated code safely. Essential for coding assistants, data analysis agents, and automated testing.",
        "human_uses": [
            "Let AI coding assistants run and test their own generated code",
            "Build data analysis pipelines where agents write and execute code",
            "Create interactive coding environments for AI-assisted learning",
            "Run automated tests in isolated environments"
        ],
        "agent_uses": [
            "Execute generated code without risk to the host system",
            "Run Python scripts, install packages, test outputs in isolation",
            "Persistent sandboxes that maintain state across agent turns",
            "File system access within the sandbox for complex workflows"
        ],
        "install": "pip install e2b-code-interpreter",
        "quick_start": "from e2b_code_interpreter import Sandbox\n\nwith Sandbox() as sandbox:\n    result = sandbox.run_code('import pandas as pd; print(pd.__version__)')\n    print(result.text)",
        "links": {
            "Website": "https://e2b.dev",
            "GitHub": "https://github.com/e2b-dev/e2b",
            "Docs": "https://e2b.dev/docs",
            "PyPI": "https://pypi.org/project/e2b"
        }
    },
    "devinai": {
        "name": "Devin AI",
        "emoji": "💻",
        "category": "Autonomous Software Engineer",
        "tagline": "AI software engineer that codes, runs, and ships autonomously",
        "description": "Devin (from Cognition) is a fully autonomous AI software engineer. It can read requirements, write code, run tests, fix bugs, and deploy — all without human intervention. Operates in a sandboxed environment with a browser, terminal, and code editor.",
        "best_for": "End-to-end software engineering tasks: building features from spec, fixing bugs from issue descriptions, setting up infrastructure, and maintaining codebases.",
        "human_uses": [
            "Delegate entire engineering tasks from spec to deployment",
            "Automatically fix GitHub issues end-to-end",
            "Build and deploy web apps from a description",
            "Onboard to unfamiliar codebases with AI that reads and navigates them"
        ],
        "agent_uses": [
            "Reference architecture for autonomous software agent design",
            "Use as a specialized sub-agent for coding tasks in a multi-agent system"
        ],
        "install": "Hosted service — waitlist / enterprise access\n# Visit: cognition.ai/devin",
        "quick_start": "# Request access at cognition.ai\n# Then use via the Devin web interface or API",
        "links": {
            "Website": "https://cognition.ai/devin",
            "Blog": "https://cognition.ai/blog/introducing-devin"
        }
    },
    "manusai": {
        "name": "Manus AI",
        "emoji": "🖐️",
        "category": "General Autonomous Agent",
        "tagline": "General-purpose autonomous agent for complex real-world tasks",
        "description": "Manus is a general-purpose autonomous agent that can browse the web, write and run code, manage files, and complete multi-step tasks. Developed by a Chinese AI startup, it gained attention for strong performance on complex agentic benchmarks.",
        "best_for": "Complex, multi-step tasks that require combining web research, code execution, and document generation. Good benchmark for comparing against other general-purpose agents.",
        "human_uses": [
            "Research and compile reports from multiple web sources",
            "Automate data collection and analysis workflows",
            "Complete multi-step tasks across different tools and contexts",
            "Handle administrative tasks that require judgment"
        ],
        "agent_uses": [
            "Reference for general-purpose agent architecture patterns",
            "Benchmark comparison for evaluating agent capability"
        ],
        "install": "Hosted service — access via manus.im\n# Limited regional availability",
        "quick_start": "# Visit manus.im for access\n# Primarily available in Asian markets",
        "links": {
            "Website": "https://manus.im"
        }
    },
    "claudebot": {
        "name": "Claude (Anthropic)",
        "emoji": "🧡",
        "category": "Foundation Model / API",
        "tagline": "Anthropic's frontier AI — strong reasoning, large context, safety-focused",
        "description": "Claude is Anthropic's family of large language models, available via API and claude.ai. Known for strong reasoning, very large context windows (200k tokens), nuanced writing, and safety alignment. Powers many autonomous agents via the Anthropic API or third-party gateways.",
        "best_for": "Complex reasoning, long-document analysis, coding, and nuanced writing tasks. The large context window makes it ideal for agents that need to process full codebases, reports, or long conversations.",
        "human_uses": [
            "Long-document analysis and summarization",
            "Complex coding tasks and debugging",
            "Nuanced writing, editing, and content creation",
            "Research synthesis across multiple sources"
        ],
        "agent_uses": [
            "Primary reasoning engine for autonomous agents via Anthropic API",
            "200k context window enables agents to process entire codebases",
            "Tool use (function calling) for structured agent action execution",
            "Strong instruction-following for reliable agentic behavior"
        ],
        "install": "pip install anthropic",
        "quick_start": "import anthropic\nclient = anthropic.Anthropic(api_key='sk-ant-...')\nmessage = client.messages.create(\n    model='claude-sonnet-4-5',\n    max_tokens=1024,\n    messages=[{'role': 'user', 'content': 'Hello!'}]\n)",
        "links": {
            "Website": "https://claude.ai",
            "API Docs": "https://docs.anthropic.com",
            "PyPI": "https://pypi.org/project/anthropic",
            "Models": "https://docs.anthropic.com/en/docs/about-claude/models"
        }
    },
    "gpt-assistant": {
        "name": "GPT / OpenAI API",
        "emoji": "🟢",
        "category": "Foundation Model / API",
        "tagline": "OpenAI's GPT models — the most widely integrated AI API",
        "description": "OpenAI's GPT-4 and GPT-4o models are the most widely used AI APIs in the world. Available via REST API, Python/JS SDKs, and the Assistants API (which adds persistent threads, file search, and code interpreter). Foundation for most AI products built in 2023-2024.",
        "best_for": "Integration into existing products via API. The Assistants API provides a managed layer for building agents with memory, file access, and tool use without managing state yourself.",
        "human_uses": [
            "Build AI features into any application via REST API",
            "Use Assistants API for stateful, multi-turn AI assistants",
            "Fine-tune models on custom data for specialized tasks",
            "Access multimodal capabilities (vision, audio) via GPT-4o"
        ],
        "agent_uses": [
            "Function calling for structured agent tool use",
            "Assistants API for managed agent threads and memory",
            "Batch API for high-throughput agent workloads",
            "Most agent frameworks support OpenAI API out of the box"
        ],
        "install": "pip install openai",
        "quick_start": "from openai import OpenAI\nclient = OpenAI(api_key='sk-...')\nresponse = client.chat.completions.create(\n    model='gpt-4o',\n    messages=[{'role': 'user', 'content': 'Hello'}]\n)",
        "links": {
            "Website": "https://openai.com",
            "API Docs": "https://platform.openai.com/docs",
            "PyPI": "https://pypi.org/project/openai",
            "Playground": "https://platform.openai.com/playground"
        }
    },
    "gemini-advanced": {
        "name": "Gemini (Google)",
        "emoji": "💠",
        "category": "Foundation Model / API",
        "tagline": "Google's multimodal AI — strong reasoning, generous free tier",
        "description": "Gemini is Google's family of frontier AI models, ranging from Flash (fast, cheap) to Pro (balanced) to Ultra (most capable). Available via Google AI Studio, Vertex AI, and the Gemini API. Notable for multimodal capabilities, 1M+ token context windows, and a generous free tier.",
        "best_for": "Cost-sensitive agent deployments (Flash is very cheap), long-context tasks (1M token window), and multimodal applications. Google Workspace integration makes it useful for enterprise.",
        "human_uses": [
            "Use Gemini 1.5 Flash for high-volume, low-cost AI tasks",
            "Process hour-long videos or massive documents in one context",
            "Integrate AI into Google Workspace (Docs, Sheets, Gmail)",
            "Build multimodal applications with image, audio, video understanding"
        ],
        "agent_uses": [
            "High-volume agent tasks with Gemini Flash (low cost per token)",
            "Long-context agents that need to process huge documents",
            "Free-tier agents for development and experimentation",
            "Google Cloud integration for enterprise agent deployments"
        ],
        "install": "pip install google-generativeai",
        "quick_start": "import google.generativeai as genai\ngenai.configure(api_key='AIza...')\nmodel = genai.GenerativeModel('gemini-2.0-flash')\nresponse = model.generate_content('Hello!')\nprint(response.text)",
        "links": {
            "Website": "https://deepmind.google/technologies/gemini",
            "API Docs": "https://ai.google.dev/gemini-api/docs",
            "AI Studio": "https://aistudio.google.com",
            "PyPI": "https://pypi.org/project/google-generativeai"
        }
    },
    "perplexityai": {
        "name": "Perplexity AI",
        "emoji": "🔍",
        "category": "Search + AI",
        "tagline": "AI-powered search with citations — always up-to-date answers",
        "description": "Perplexity is an AI-powered search engine that provides cited, real-time answers. Unlike static LLMs, it searches the web for every query. Available as a consumer product and via API (the Sonar API). Agents can use it to get current information without managing their own web search.",
        "best_for": "Any use case requiring current information with sources. Much simpler than implementing your own search pipeline — just call the API and get cited results.",
        "human_uses": [
            "Research questions that require current, cited information",
            "Fact-checking AI outputs with real sources",
            "Quick research without sifting through search results manually",
            "Deep research mode for comprehensive topic exploration"
        ],
        "agent_uses": [
            "Web search with citations via Sonar API (no scraping needed)",
            "Real-time information for agents that can't be retrained",
            "Research subtask delegation in multi-agent systems",
            "Grounded answers that reduce hallucination risk"
        ],
        "install": "pip install openai  # Sonar API uses OpenAI-compatible interface",
        "quick_start": "from openai import OpenAI\nclient = OpenAI(api_key='pplx-...', base_url='https://api.perplexity.ai')\nresponse = client.chat.completions.create(\n    model='sonar-pro',\n    messages=[{'role': 'user', 'content': 'Latest AI agent frameworks 2025?'}]\n)",
        "links": {
            "Website": "https://perplexity.ai",
            "API Docs": "https://docs.perplexity.ai",
            "Pricing": "https://docs.perplexity.ai/guides/pricing"
        }
    },
    "elevenlabs": {
        "name": "ElevenLabs",
        "emoji": "🎙️",
        "category": "Audio AI",
        "tagline": "Best-in-class text-to-speech and voice cloning API",
        "description": "ElevenLabs provides the most natural-sounding text-to-speech API available. Supports voice cloning (create a custom voice from a few minutes of audio), multilingual synthesis, and real-time audio streaming. Widely used in AI agents that need to communicate via voice.",
        "best_for": "Agents and applications that need high-quality voice output. Voice cloning makes it possible to create a consistent, recognizable voice identity for your agent.",
        "human_uses": [
            "Add voice output to any AI application",
            "Clone your own voice for personalized AI assistants",
            "Create audiobooks and podcasts from text",
            "Build voice-based customer service agents"
        ],
        "agent_uses": [
            "Voice identity for agents operating in voice interfaces",
            "Text-to-speech for agent notifications and summaries",
            "Multilingual voice output without separate translation steps",
            "Real-time streaming for low-latency voice interactions"
        ],
        "install": "pip install elevenlabs",
        "quick_start": "from elevenlabs.client import ElevenLabs\nclient = ElevenLabs(api_key='xi-api-key-...')\naudio = client.generate(\n    text='Hello from your AI agent',\n    voice='Rachel',\n    model='eleven_multilingual_v2'\n)",
        "links": {
            "Website": "https://elevenlabs.io",
            "API Docs": "https://elevenlabs.io/docs",
            "PyPI": "https://pypi.org/project/elevenlabs",
            "Voice Library": "https://elevenlabs.io/voice-library"
        }
    },
    "runway": {
        "name": "Runway",
        "emoji": "🎬",
        "category": "Video AI",
        "tagline": "AI video generation and editing — text or image to video",
        "description": "Runway is a generative AI platform for video creation. Gen-3 Alpha and later models can generate high-quality video from text prompts or images. Used by filmmakers, content creators, and AI pipelines that need video generation capabilities.",
        "best_for": "Content creation workflows requiring video generation. The API makes it accessible to agents that need to produce video assets programmatically.",
        "human_uses": [
            "Generate video from text descriptions for content creation",
            "Animate still images into video clips",
            "Create visual effects and scene generation for film",
            "Build automated video content pipelines"
        ],
        "agent_uses": [
            "Generate video assets in automated content pipelines",
            "Create visual demonstrations from text descriptions",
            "Produce video summaries or explainers autonomously"
        ],
        "install": "pip install runwayml",
        "quick_start": "import runwayml\nclient = runwayml.RunwayML(api_key='key_...')\ntask = client.image_to_video.create(\n    model='gen3a_turbo',\n    prompt_image='https://example.com/image.jpg',\n    prompt_text='camera pans slowly right'\n)",
        "links": {
            "Website": "https://runwayml.com",
            "API Docs": "https://docs.dev.runwayml.com",
            "PyPI": "https://pypi.org/project/runwayml"
        }
    },
    "midjourney": {
        "name": "Midjourney",
        "emoji": "🎨",
        "category": "Image Generation",
        "tagline": "Leading AI image generation — stunning artistic output",
        "description": "Midjourney is the most widely used AI image generation platform. Operates through Discord (and a new web UI). Known for distinctive aesthetic quality, especially for artistic and conceptual imagery. No official public API — third-party integrations via Discord automation.",
        "best_for": "High-quality artistic image generation for creative projects. If you need the best-looking images, Midjourney is the benchmark.",
        "human_uses": [
            "Generate concept art, illustrations, and design mockups",
            "Create consistent visual styles for projects and brands",
            "Explore creative visual ideas quickly",
            "Produce social media and marketing imagery"
        ],
        "agent_uses": [
            "Image generation via Discord automation (unofficial — fragile)",
            "Better alternatives for agents: DALL-E 3 API or Stable Diffusion API",
            "Reference for image quality benchmarking"
        ],
        "install": "No install — uses Discord\n# Join: discord.gg/midjourney\n# Or use web UI: midjourney.com",
        "quick_start": "# Via Discord:\n# /imagine prompt: your image description --ar 16:9\n\n# No official API yet — use DALL-E or Stability AI for agent automation",
        "links": {
            "Website": "https://midjourney.com",
            "Discord": "https://discord.gg/midjourney",
            "Documentation": "https://docs.midjourney.com"
        }
    },
    "pi-ai": {
        "name": "Pi AI",
        "emoji": "π",
        "category": "Conversational AI",
        "tagline": "Inflection's emotionally intelligent personal AI",
        "description": "Pi is a personal AI from Inflection, designed for supportive, emotionally intelligent conversations. Different from task-oriented assistants — Pi is built for ongoing personal relationships, reflection, and wellbeing support. Limited API access; primarily a consumer product.",
        "best_for": "Personal, relationship-focused AI interactions. Not ideal for technical or agentic tasks — better for users seeking a conversational companion rather than a task executor.",
        "human_uses": [
            "Thoughtful, supportive conversations about personal topics",
            "Journaling and reflection partner",
            "Emotional support and active listening",
            "Casual, ongoing relationship-style AI interaction"
        ],
        "agent_uses": [
            "Limited — Pi is not designed for agentic use",
            "Reference for conversational AI design and tone"
        ],
        "install": "Consumer product — no public API\n# Use via: pi.ai or mobile apps",
        "quick_start": "# Visit pi.ai to start a conversation\n# Available on iOS and Android",
        "links": {
            "Website": "https://pi.ai",
            "iOS App": "https://apps.apple.com/app/pi-ai/id6443772061"
        }
    },
    "jasperai": {
        "name": "Jasper AI",
        "emoji": "✍️",
        "category": "Content AI",
        "tagline": "AI writing platform for marketing and brand content",
        "description": "Jasper is an AI writing platform designed for marketing teams. It includes brand voice settings, templates for different content types, SEO integration, and team collaboration. Built on top of GPT-4 and other models with marketing-specific prompting.",
        "best_for": "Marketing teams that need consistent, brand-aligned AI content at scale. Better than raw GPT-4 for marketers because of the built-in brand voice and template system.",
        "human_uses": [
            "Generate on-brand marketing copy at scale",
            "Create consistent content across channels with brand voice",
            "Produce SEO-optimized blog posts and landing pages",
            "Collaborate on AI content within teams"
        ],
        "agent_uses": [
            "Content generation via Jasper API with brand constraints",
            "Faster than prompt-engineering GPT-4 for marketing-specific tasks"
        ],
        "install": "API access via jasper.ai/api\n# Python: pip install requests (REST API)",
        "quick_start": "# REST API\nimport requests\nresponse = requests.post(\n    'https://api.jasper.ai/v1/commands/outputs',\n    headers={'X-API-Key': 'your-key'},\n    json={'inputs': {'command': 'Write a tweet about AI agents'}}\n)",
        "links": {
            "Website": "https://jasper.ai",
            "API Docs": "https://developers.jasper.ai"
        }
    },
    "copyai": {
        "name": "Copy.ai",
        "emoji": "📋",
        "category": "Content AI",
        "tagline": "AI-powered copywriting and GTM workflow automation",
        "description": "Copy.ai started as an AI copywriting tool and has evolved into a go-to-market (GTM) AI platform. Includes templates for sales copy, marketing content, and workflows that chain AI tasks together. Offers an API for integrating into custom pipelines.",
        "best_for": "Sales and marketing copy generation at scale. The GTM focus makes it better than generic LLMs for conversion-optimized content.",
        "human_uses": [
            "Generate sales emails, product descriptions, and ad copy",
            "Build GTM workflows that chain content tasks automatically",
            "Create landing pages, social posts, and blog intros quickly",
            "Scale content production without proportional headcount"
        ],
        "agent_uses": [
            "Content generation API for marketing-specialized output",
            "Workflow automation for content pipelines"
        ],
        "install": "pip install requests  # REST API access",
        "quick_start": "# API at api.copy.ai\nimport requests\nresponse = requests.post(\n    'https://api.copy.ai/api/workflow',\n    headers={'x-copy-ai-api-key': 'your-key'},\n    json={'workflowId': 'your-workflow-id', 'startVariables': {}}\n)",
        "links": {
            "Website": "https://copy.ai",
            "API Docs": "https://docs.copy.ai"
        }
    },
    "notionai": {
        "name": "Notion AI",
        "emoji": "📓",
        "category": "Productivity AI",
        "tagline": "AI built into your Notion workspace",
        "description": "Notion AI is an AI layer embedded directly inside Notion. It can write, summarize, translate, and answer questions about your Notion pages. Available as an add-on to any Notion workspace. The Notion API also allows agents to read/write Notion databases programmatically.",
        "best_for": "Teams already using Notion who want AI assistance without switching tools. The Notion API (separate from Notion AI) is useful for agents that need to manage structured data in Notion databases.",
        "human_uses": [
            "Summarize long Notion pages with one click",
            "Draft content directly in your workspace",
            "Auto-fill database properties with AI",
            "Translate pages and improve writing in-place"
        ],
        "agent_uses": [
            "Read/write Notion databases via the Notion API",
            "Use Notion as a structured task/project management backend",
            "Sync agent outputs to Notion for human review",
            "Query Notion knowledge bases as agent memory"
        ],
        "install": "pip install notion-client  # For Notion API (not Notion AI)\n# Notion AI: add-on via Notion settings",
        "quick_start": "from notion_client import Client\nnotion = Client(auth='ntn_...')\npage = notion.pages.retrieve(page_id='page-id')\n# Or search:\nresults = notion.search(query='AI agents').get('results')",
        "links": {
            "Notion AI": "https://notion.so/product/ai",
            "API Docs": "https://developers.notion.com",
            "PyPI": "https://pypi.org/project/notion-client"
        }
    },
    "grammarlyai": {
        "name": "Grammarly AI",
        "emoji": "✏️",
        "category": "Writing AI",
        "tagline": "AI writing assistant focused on clarity, tone, and correctness",
        "description": "Grammarly uses AI to improve writing quality: grammar, spelling, clarity, engagement, and tone. The Grammarly API and SDK allow integration into custom applications. Useful for agents that produce text output intended for human readers.",
        "best_for": "Post-processing agent-generated text before it reaches humans. Grammarly can catch tone issues and clarity problems that LLMs sometimes miss.",
        "human_uses": [
            "Improve writing quality across any application (browser extension)",
            "Check tone and formality for emails and messages",
            "Catch grammar and style issues in real-time",
            "Rewrite sentences for clarity with AI suggestions"
        ],
        "agent_uses": [
            "Post-process agent-generated text for quality before publishing",
            "Check tone of agent messages before sending to users",
            "Integrate via Grammarly Text Editor SDK for in-app writing assistance"
        ],
        "install": "# Browser extension: grammarly.com/install\n# SDK: npm install @grammarly/editor-sdk",
        "quick_start": "// Grammarly Text Editor SDK\nimport Grammarly from '@grammarly/editor-sdk'\nconst grammarly = await Grammarly.init('client_id')\nconst plugin = grammarly.withPlugin(editor, { documentId: 'doc-1' })",
        "links": {
            "Website": "https://grammarly.com",
            "For Developers": "https://developer.grammarly.com",
            "Text Editor SDK": "https://developer.grammarly.com/text-editor-sdk"
        }
    },
    "characterai": {
        "name": "Character AI",
        "emoji": "🎭",
        "category": "Conversational AI / Roleplay",
        "tagline": "Talk to AI personas — millions of community-created characters",
        "description": "Character AI allows users to chat with AI-powered characters — historical figures, fictional characters, and custom personas created by the community. Built on custom LLMs optimized for character consistency and engaging conversation. Primarily a consumer platform with limited API access.",
        "best_for": "Entertainment, education through roleplay, and language learning via conversation. Not designed for task-oriented or agentic use.",
        "human_uses": [
            "Roleplay with fictional or historical characters",
            "Language practice with conversational AI",
            "Creative storytelling and collaborative fiction",
            "Entertainment and social interaction with AI personas"
        ],
        "agent_uses": [
            "Limited — not designed for agent use",
            "Reference for persona consistency and character design in conversational AI"
        ],
        "install": "Consumer product — no public API\n# Use via: character.ai or mobile apps",
        "quick_start": "# Visit character.ai to browse and chat with characters",
        "links": {
            "Website": "https://character.ai",
            "iOS App": "https://apps.apple.com/app/character-ai/id1640750767"
        }
    },
    "braveleo": {
        "name": "Brave Leo",
        "emoji": "🦁",
        "category": "Browser AI",
        "tagline": "Privacy-first AI assistant built into Brave Browser",
        "description": "Leo is Brave's built-in AI assistant. Available directly in the Brave browser sidebar, it can summarize pages, answer questions about content you're viewing, and chat — all with Brave's privacy guarantees (no data logging by default). Uses Llama and Claude models.",
        "best_for": "Privacy-conscious users who want AI assistance without data being sent to third-party AI services. Tight browser integration for page-specific Q&A.",
        "human_uses": [
            "Summarize any webpage you're reading with one click",
            "Ask questions about the current page without copy-pasting",
            "Get AI assistance without leaving your browser",
            "Privacy-preserving AI that doesn't log your conversations"
        ],
        "agent_uses": [
            "Limited — browser-embedded, not API accessible",
            "Reference for privacy-preserving AI integration patterns"
        ],
        "install": "Included with Brave Browser\n# Download Brave: brave.com/download\n# Leo: sidebar icon or Cmd+/ on Mac",
        "quick_start": "# Download Brave Browser\n# Click Leo icon in sidebar\n# Or press Cmd+/ (Mac) / Ctrl+/ (Windows)",
        "links": {
            "Website": "https://brave.com/leo",
            "Download Brave": "https://brave.com/download",
            "Models": "https://brave.com/blog/brave-leo-local-models"
        }
    },
    "openai": {
        "name": "OpenAI",
        "emoji": "🟢",
        "category": "AI Research Lab",
        "tagline": "Developer of GPT-4, ChatGPT, DALL-E, Whisper, and Sora",
        "description": "OpenAI is the company behind GPT-4, ChatGPT, DALL-E, Whisper, and Sora. As an AI research lab turned AI product company, it provides the most widely-used commercial AI APIs. The OpenAI API is the default integration target for most AI applications.",
        "best_for": "Building production AI applications with the most mature ecosystem of tools, integrations, and documentation. The Assistants API and fine-tuning make it suitable for specialized agent deployments.",
        "human_uses": [
            "Access GPT-4o, o1, and other models via API",
            "Use ChatGPT for personal AI assistance",
            "Generate images with DALL-E 3",
            "Transcribe audio with Whisper"
        ],
        "agent_uses": [
            "Assistants API: managed threads, file search, code interpreter",
            "Function calling for structured agent tool use",
            "Fine-tuning for specialized agent behavior",
            "Batch API for cost-efficient high-volume agent tasks"
        ],
        "install": "pip install openai",
        "quick_start": "from openai import OpenAI\nclient = OpenAI(api_key='sk-...')\nresponse = client.chat.completions.create(\n    model='gpt-4o',\n    messages=[{'role': 'user', 'content': 'Hello'}]\n)",
        "links": {
            "Website": "https://openai.com",
            "Platform": "https://platform.openai.com",
            "API Docs": "https://platform.openai.com/docs",
            "Status": "https://status.openai.com"
        }
    },
    "anthropic": {
        "name": "Anthropic",
        "emoji": "🧡",
        "category": "AI Research Lab",
        "tagline": "Safety-focused AI lab — creators of Claude",
        "description": "Anthropic is an AI safety company and research lab that builds the Claude family of models. Founded by former OpenAI researchers, Anthropic focuses on interpretability research, constitutional AI, and building AI systems that are safe, honest, and harmless.",
        "best_for": "Organizations that prioritize AI safety, compliance, and responsible AI development. Claude's large context window and nuanced instruction-following make it excellent for complex agentic tasks.",
        "human_uses": [
            "Access Claude models via the Anthropic API",
            "Enterprise AI with strong safety and compliance guarantees",
            "Research applications in AI safety and alignment",
            "Long-document processing with 200k token context"
        ],
        "agent_uses": [
            "Claude API for autonomous agent reasoning",
            "Tool use (function calling) for structured agent actions",
            "MCP (Model Context Protocol) for standardized tool integration",
            "Strong safety properties reduce risk in autonomous deployments"
        ],
        "install": "pip install anthropic",
        "quick_start": "import anthropic\nclient = anthropic.Anthropic(api_key='sk-ant-...')\nmessage = client.messages.create(\n    model='claude-sonnet-4-5',\n    max_tokens=1024,\n    messages=[{'role': 'user', 'content': 'Hello'}]\n)",
        "links": {
            "Website": "https://anthropic.com",
            "API Docs": "https://docs.anthropic.com",
            "PyPI": "https://pypi.org/project/anthropic",
            "Research": "https://anthropic.com/research"
        }
    },
    "googledeepmind": {
        "name": "Google DeepMind",
        "emoji": "🔵",
        "category": "AI Research Lab",
        "tagline": "Google's combined AI research division — Gemini, AlphaFold, AlphaCode",
        "description": "Google DeepMind is Google's unified AI research division, combining DeepMind and Google Brain. Responsible for Gemini, AlphaFold (protein structure prediction), AlphaCode (competitive programming), and fundamental reinforcement learning research. Access via Google Cloud and AI Studio.",
        "best_for": "Cutting-edge research capabilities and Google ecosystem integration. Gemini's massive context windows and multimodality make DeepMind's work accessible via API.",
        "human_uses": [
            "Access Gemini models via Google AI Studio (free tier available)",
            "Use AlphaFold for protein structure prediction in research",
            "Vertex AI for enterprise Google Cloud AI deployment",
            "Real-time information access via Grounding with Google Search"
        ],
        "agent_uses": [
            "Gemini Flash for cost-efficient high-volume agent tasks",
            "Gemini 1.5 Pro for million-token context agents",
            "Grounding: real-time web search integrated into model responses",
            "Vertex AI for managed, scalable agent deployments"
        ],
        "install": "pip install google-generativeai  # For Gemini API\npip install google-cloud-aiplatform  # For Vertex AI",
        "quick_start": "import google.generativeai as genai\ngenai.configure(api_key='AIza...')\nmodel = genai.GenerativeModel('gemini-2.0-flash')\nprint(model.generate_content('Hello').text)",
        "links": {
            "Website": "https://deepmind.google",
            "Gemini API": "https://ai.google.dev",
            "Vertex AI": "https://cloud.google.com/vertex-ai",
            "Research": "https://deepmind.google/research"
        }
    },
    "metaai": {
        "name": "Meta AI / Llama",
        "emoji": "🦙",
        "category": "AI Research Lab",
        "tagline": "Meta's open-weight AI models — Llama runs locally",
        "description": "Meta AI releases open-weight models (Llama 3.x, Llama 4) that anyone can download and run. This is significant: Llama models run on consumer hardware, enabling private AI inference without API calls. Also powers the Meta AI assistant in Facebook, Instagram, and WhatsApp.",
        "best_for": "Running AI locally without sending data to external APIs. Llama models on Ollama or llama.cpp give you a capable, private AI that runs on your own hardware.",
        "human_uses": [
            "Run a private AI model locally with Ollama (no API costs)",
            "Use Meta AI assistant in WhatsApp and Instagram",
            "Fine-tune Llama models on custom datasets",
            "Deploy open-weight models in air-gapped or private environments"
        ],
        "agent_uses": [
            "Local agent inference with no API costs or rate limits",
            "Private agents that never send data to external servers",
            "Ollama integration for local model serving via OpenAI-compatible API",
            "Fine-tune Llama for specialized agent behavior"
        ],
        "install": "# Run Llama locally with Ollama:\nbrew install ollama\nollama run llama3.2\n\n# Or download weights directly from huggingface.co/meta-llama",
        "quick_start": "# With Ollama:\nbrew install ollama\nollama pull llama3.2\nollama run llama3.2 'Hello!'\n\n# API (OpenAI-compatible):\ncurl http://localhost:11434/api/chat -d '{\"model\":\"llama3.2\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'",
        "links": {
            "Website": "https://ai.meta.com",
            "Llama Models": "https://llama.meta.com",
            "HuggingFace": "https://huggingface.co/meta-llama",
            "Ollama": "https://ollama.ai"
        }
    },
    "xai": {
        "name": "xAI / Grok",
        "emoji": "𝕏",
        "category": "AI Research Lab",
        "tagline": "Elon Musk's AI lab — Grok with real-time X/Twitter data",
        "description": "xAI is Elon Musk's AI company, developing the Grok family of models. Grok has real-time access to X (Twitter) data, making it uniquely capable for social media and current events analysis. Available via the xAI API and integrated into X Premium.",
        "best_for": "Real-time social media analysis and anything requiring current X/Twitter data. Also notable for releasing open weights (Grok-1).",
        "human_uses": [
            "Real-time X/Twitter analysis and trend monitoring",
            "Current events Q&A with live social media context",
            "Image understanding with Grok Vision",
            "X Premium subscribers get Grok access directly in X"
        ],
        "agent_uses": [
            "Real-time X data access without Twitter API costs",
            "Social sentiment analysis and trend detection",
            "Open-weight Grok-1 for private local deployment"
        ],
        "install": "pip install openai  # xAI uses OpenAI-compatible API",
        "quick_start": "from openai import OpenAI\nclient = OpenAI(\n    api_key='xai-...',\n    base_url='https://api.x.ai/v1'\n)\nresponse = client.chat.completions.create(\n    model='grok-3',\n    messages=[{'role': 'user', 'content': 'What is trending on X today?'}]\n)",
        "links": {
            "Website": "https://x.ai",
            "API Docs": "https://docs.x.ai",
            "Grok on X": "https://x.com/i/grok"
        }
    },
    "mistralai": {
        "name": "Mistral AI",
        "emoji": "💨",
        "category": "AI Research Lab",
        "tagline": "European frontier AI — efficient models, open weights, strong API",
        "description": "Mistral AI is a French AI lab producing frontier models known for efficiency. Mistral 7B and Mixtral 8x7B are widely used open-weight models. Mistral Large and Mistral Medium via the API compete with GPT-4 and Claude at lower cost. Strong European data sovereignty story.",
        "best_for": "Cost-efficient API inference with strong capability, or local deployment via open-weight models. Good choice for European businesses with data residency requirements.",
        "human_uses": [
            "Cost-efficient API for high-volume AI tasks",
            "Run open-weight models locally for privacy",
            "European data residency compliance",
            "Codestral for code-specific tasks"
        ],
        "agent_uses": [
            "Cheap inference for high-volume agent subtasks",
            "Local Mistral models via Ollama for private agents",
            "Function calling support for structured agent tool use",
            "Codestral for code generation in agent pipelines"
        ],
        "install": "pip install mistralai\n\n# Or run locally:\nbrew install ollama && ollama run mistral",
        "quick_start": "from mistralai import Mistral\nclient = Mistral(api_key='your-key')\nresponse = client.chat.complete(\n    model='mistral-large-latest',\n    messages=[{'role': 'user', 'content': 'Hello'}]\n)",
        "links": {
            "Website": "https://mistral.ai",
            "API Docs": "https://docs.mistral.ai",
            "PyPI": "https://pypi.org/project/mistralai",
            "La Plateforme": "https://console.mistral.ai"
        }
    },
    "cohere": {
        "name": "Cohere",
        "emoji": "🔗",
        "category": "AI Research Lab / Enterprise NLP",
        "tagline": "Enterprise NLP — embeddings, RAG, and command models",
        "description": "Cohere focuses on enterprise NLP applications. Best known for its embedding models (used in RAG pipelines), the Rerank API (re-ranks search results for relevance), and Command models (optimized for business tasks). Strong enterprise deployment story with private cloud options.",
        "best_for": "Enterprise RAG (retrieval-augmented generation) pipelines. Cohere's embedding and rerank APIs are best-in-class for search and information retrieval.",
        "human_uses": [
            "Build RAG systems with best-in-class embeddings",
            "Improve search relevance with the Rerank API",
            "Enterprise AI deployment with private cloud options",
            "Multilingual NLP for global enterprise applications"
        ],
        "agent_uses": [
            "Embed documents for vector search in agent memory systems",
            "Rerank search results before passing to agent context",
            "Command R+ for long-context RAG with citations",
            "Private cloud deployment for regulated industry agents"
        ],
        "install": "pip install cohere",
        "quick_start": "import cohere\nco = cohere.ClientV2(api_key='your-key')\n# Embeddings:\nembeddings = co.embed(texts=['Hello world'], model='embed-v4.0', input_type='search_document')\n# Chat:\nresponse = co.chat(model='command-r-plus', messages=[{'role':'user','content':'Hello'}])",
        "links": {
            "Website": "https://cohere.com",
            "API Docs": "https://docs.cohere.com",
            "PyPI": "https://pypi.org/project/cohere",
            "Dashboard": "https://dashboard.cohere.com"
        }
    },
    "inflection": {
        "name": "Inflection AI",
        "emoji": "🌀",
        "category": "AI Research Lab",
        "tagline": "Creators of Pi — now an enterprise AI platform",
        "description": "Inflection AI created Pi (the personal AI) and then pivoted to enterprise AI. Most of the team (including co-founder Mustafa Suleyman) moved to Microsoft. The remaining Inflection focuses on Inflection-3, an enterprise AI model. Primarily of historical significance now.",
        "best_for": "Historical reference in the AI landscape. The enterprise Inflection-3 model is available for API access but has limited ecosystem compared to OpenAI, Anthropic, or Google.",
        "human_uses": [
            "Enterprise AI via Inflection-3 API",
            "Pi personal AI for conversational use"
        ],
        "agent_uses": [
            "Limited ecosystem — not a common choice for agent development",
            "Reference for AI company trajectory and pivot patterns"
        ],
        "install": "pip install requests  # REST API access",
        "quick_start": "# API access via inflection.ai\n# Limited documentation available",
        "links": {
            "Website": "https://inflection.ai",
            "Pi AI": "https://pi.ai"
        }
    },
    "adeptai": {
        "name": "Adept AI",
        "emoji": "🎯",
        "category": "Computer-Use AI",
        "tagline": "AI that operates software through natural language",
        "description": "Adept built AI models that can directly use computer software — clicking buttons, filling forms, navigating UIs — based on natural language instructions. Their Action Transformer (ACT) model was an early pioneer in computer-use AI. Primarily enterprise focused.",
        "best_for": "Automating software workflows where you can't use an API — legacy enterprise software, complex UIs, and repetitive computer tasks.",
        "human_uses": [
            "Automate repetitive software workflows without APIs",
            "Navigate complex enterprise software by describing what to do",
            "RPA-style automation with AI flexibility"
        ],
        "agent_uses": [
            "Reference architecture for computer-use agent design",
            "Now largely superseded by Claude's computer-use API for most use cases"
        ],
        "install": "Enterprise product — contact adept.ai for access",
        "quick_start": "# Enterprise sales process\n# Contact: adept.ai/enterprise",
        "links": {
            "Website": "https://adept.ai"
        }
    },
    "linkstack": {
        "name": "LinkStack",
        "emoji": "🔗",
        "category": "Open-Source Link Page",
        "tagline": "Self-hosted Linktree alternative for agents and creators",
        "description": "LinkStack is an open-source, self-hosted platform for creating link-in-bio pages. Similar to Linktree but you own your data and host it yourself. Useful for agents and creators who want a central hub for their online presence without giving data to a third-party service.",
        "best_for": "Agents and creators who want a customizable, privacy-respecting link page without Linktree's data practices. Self-hosting gives you full control.",
        "human_uses": [
            "Create a central hub for all your links and social profiles",
            "Self-host instead of using Linktree for data privacy",
            "Customize link pages beyond what Linktree allows",
            "Multiple users on one instance"
        ],
        "agent_uses": [
            "Agent identity hub: central page linking to all agent profiles",
            "Self-hosted for full control of agent's public presence",
            "API-accessible link management for automated updates"
        ],
        "install": "# Docker:\ndocker run -d -p 80:80 \\\n  -v linkstack_data:/htdocs \\\n  linkstackorg/linkstack",
        "quick_start": "# Docker (easiest):\ndocker run -d -p 80:80 \\\n  -v linkstack:/htdocs \\\n  linkstackorg/linkstack\n\n# Then visit http://localhost to set up",
        "links": {
            "Website": "https://linkstack.org",
            "GitHub": "https://github.com/LinkStackOrg/LinkStack",
            "Docker Hub": "https://hub.docker.com/r/linkstackorg/linkstack"
        }
    }
}

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} | Tools & Platforms | AgentFolio</title>
    <meta name="description" content="{description_short}">
    <style>
        :root {{
            --bg: #0a0a12;
            --surface: #12121f;
            --surface2: #1a1a2e;
            --border: #2a2a3e;
            --text: #e8e8f0;
            --muted: #6b6b8a;
            --accent: #a78bfa;
            --accent-dark: #7c3aed;
            --green: #22c55e;
            --blue: #60a5fa;
            --yellow: #fbbf24;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 2rem 1rem; line-height: 1.6; }}
        .container {{ max-width: 700px; margin: 0 auto; }}
        .back {{ color: var(--muted); text-decoration: none; font-size: 0.85rem; display: inline-block; margin-bottom: 1.5rem; }}
        .back:hover {{ color: var(--accent); }}
        .hero {{ background: linear-gradient(135deg, var(--accent-dark), var(--accent)); padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem; text-align: center; }}
        .hero-emoji {{ font-size: 3rem; margin-bottom: 0.5rem; }}
        .hero-name {{ font-size: 2rem; font-weight: 800; margin-bottom: 0.25rem; }}
        .hero-category {{ font-size: 0.85rem; opacity: 0.85; background: rgba(0,0,0,0.2); display: inline-block; padding: 0.2rem 0.75rem; border-radius: 99px; margin-bottom: 0.75rem; }}
        .hero-tagline {{ font-size: 1.05rem; opacity: 0.9; }}
        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; }}
        .card h2 {{ font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.75rem; }}
        .card p {{ color: var(--text); font-size: 0.95rem; }}
        .card ul {{ list-style: none; }}
        .card ul li {{ padding: 0.35rem 0; color: var(--text); font-size: 0.9rem; border-bottom: 1px solid var(--border); }}
        .card ul li:last-child {{ border-bottom: none; }}
        .card ul li::before {{ content: "→ "; color: var(--accent); font-weight: bold; }}
        .use-case-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }}
        .use-case-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; }}
        .use-case-card h2 {{ font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.75rem; }}
        .use-case-card.human h2 {{ color: var(--blue); }}
        .use-case-card.agent h2 {{ color: var(--green); }}
        .use-case-card ul {{ list-style: none; }}
        .use-case-card ul li {{ padding: 0.3rem 0; font-size: 0.88rem; border-bottom: 1px solid var(--border); }}
        .use-case-card ul li:last-child {{ border-bottom: none; }}
        .code-block {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 1rem; font-family: 'SF Mono', Menlo, Monaco, monospace; font-size: 0.82rem; overflow-x: auto; color: var(--accent); white-space: pre; margin-top: 0.5rem; }}
        .links-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.5rem; margin-top: 0.5rem; }}
        .link-btn {{ display: block; text-align: center; padding: 0.5rem 0.75rem; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; color: var(--accent); text-decoration: none; font-size: 0.85rem; transition: background 0.15s; }}
        .link-btn:hover {{ background: var(--accent-dark); color: white; border-color: var(--accent-dark); }}
        @media (max-width: 600px) {{ .use-case-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
<div class="container">
    <a href="../../" class="back">← Back to AgentFolio</a>

    <div class="hero">
        <div class="hero-emoji">{emoji}</div>
        <div class="hero-name">{name}</div>
        <span class="hero-category">{category}</span>
        <div class="hero-tagline">{tagline}</div>
    </div>

    <div class="card">
        <h2>What it is</h2>
        <p>{description}</p>
    </div>

    <div class="card">
        <h2>Best for</h2>
        <p>{best_for}</p>
    </div>

    <div class="use-case-grid">
        <div class="use-case-card human">
            <h2>👤 Human use cases</h2>
            <ul>{human_uses_html}</ul>
        </div>
        <div class="use-case-card agent">
            <h2>🤖 Agent use cases</h2>
            <ul>{agent_uses_html}</ul>
        </div>
    </div>

    <div class="card">
        <h2>How to install / get access</h2>
        <div class="code-block">{install}</div>
        {quickstart_html}
    </div>

    <div class="card">
        <h2>Links</h2>
        <div class="links-grid">{links_html}</div>
    </div>

    <div style="text-align:center; margin-top:2rem; color:var(--muted); font-size:0.8rem;">
        <a href="../../" style="color:var(--accent);">AgentFolio</a> — tracking autonomous AI agents
    </div>
</div>
</body>
</html>'''


def make_page(handle, tool):
    human_uses_html = "\n".join(f"<li>{u}</li>" for u in tool["human_uses"])
    agent_uses_html = "\n".join(f"<li>{u}</li>" for u in tool["agent_uses"])
    links_html = "\n".join(
        f'<a href="{url}" target="_blank" class="link-btn">{label}</a>'
        for label, url in tool["links"].items()
    )
    quickstart = tool.get("quick_start", "")
    quickstart_html = f'<div class="code-block">{quickstart}</div>' if quickstart else ""
    desc_short = tool["description"][:160].rstrip() + "..."

    return HTML_TEMPLATE.format(
        name=tool["name"],
        emoji=tool["emoji"],
        category=tool["category"],
        tagline=tool["tagline"],
        description=tool["description"],
        description_short=desc_short,
        best_for=tool["best_for"],
        human_uses_html=human_uses_html,
        agent_uses_html=agent_uses_html,
        install=tool["install"],
        quickstart_html=quickstart_html,
        links_html=links_html,
    )


def main():
    base = "/Users/serenerenze/bob-bootstrap/projects/agentrank"
    tool_dir = os.path.join(base, "tool")
    os.makedirs(tool_dir, exist_ok=True)

    count = 0
    for handle, tool in TOOLS.items():
        page_dir = os.path.join(tool_dir, handle)
        os.makedirs(page_dir, exist_ok=True)
        page_path = os.path.join(page_dir, "index.html")
        with open(page_path, "w") as f:
            f.write(make_page(handle, tool))
        print(f"✅ {handle}: {tool['name']}")
        count += 1

    print(f"\n✅ Generated {count} tool pages in {tool_dir}/")


if __name__ == "__main__":
    main()
