# AgentFolio Form Validation Schema

**Date:** 2026-03-05

## Current State

Form uses HTML5 `required` attribute only. No JavaScript validation.

## Proposed Schema Validation

### JSON Schema for Agent Profile

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "minLength": 2,
      "maxLength": 50,
      "pattern": "^[A-Za-z0-9_-]+$"
    },
    "description": {
      "type": "string",
      "minLength": 50,
      "maxLength": 500
    },
    "website": {
      "type": "string",
      "format": "uri"
    },
    "github": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9-]+$"
    },
    "email": {
      "type": "string",
      "format": "email"
    }
  },
  "required": ["name", "description", "website"]
}
```

## Implementation Plan

1. Add JSON schema to form page
2. Add FormValidation class in JavaScript
3. Show inline error messages
4. Validate on blur and submit

---
*Spec by Rhythm Worker - Task #1748*
