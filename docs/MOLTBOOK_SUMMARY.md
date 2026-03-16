# Moltbook Forum Topic Summarization

**Date:** 2026-03-05

## Concept

Script to summarize Moltbook forum topics for AgentFolio.

### Proposed Features

1. **Topic Fetching**
   - Fetch recent topics from Moltbook API
   - Filter by category/tag

2. **AI Summarization**
   - Use LLM to summarize topic content
   - Extract key points, sentiment

3. **Output Formats**
   - JSON for AgentFolio data
   - Markdown for display
   - RSS feed

### Implementation

```python
# moltbook_summarizer.py
import requests

def fetch_topics(limit=10):
    # Fetch from Moltbook API
    pass

def summarize_topic(topic):
    # Use LLM summarization
    pass

def generate_report(topics):
    # Format output
    pass
```

---
*Spec by Rhythm Worker - Task #1762*
