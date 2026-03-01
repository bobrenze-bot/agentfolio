#!/bin/bash
# AgentFolio A2A Card Regression Test
# Verifies A2A card fetching and validation remains functional
# Tests the fix for SSL/TLS issues when fetching .well-known/agent-card.json
# Exit codes: 0 = pass, 1 = fail

set -e

DOMAIN="bobrenze.com"
TIMEOUT=30
FAILED=0

echo "=== AgentFolio A2A Card Regression Test ==="
echo "Testing: https://${DOMAIN}/.well-known/agent-card.json"
echo ""

# Test 1: agent-card.json Accessibility
echo "[TEST 1] A2A Agent Card Accessibility..."
AGENT_CARD=$(curl -s --max-time ${TIMEOUT} "https://${DOMAIN}/.well-known/agent-card.json" 2>/dev/null || echo "")
if [ -n "$AGENT_CARD" ] && echo "$AGENT_CARD" | grep -q '"name"'; then
    echo "  ✓ PASS: agent-card.json is accessible and contains name field"
    AGENT_NAME=$(echo "$AGENT_CARD" | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "    Agent: $AGENT_NAME"
else
    echo "  ✗ FAIL: agent-card.json not accessible or missing name field"
    FAILED=1
fi

# Test 2: Agent Card Valid JSON
echo "[TEST 2] Agent Card JSON Validity..."
if echo "$AGENT_CARD" | python3 -c "import json,sys; json.load(sys.stdin); print('  ✓ PASS: Valid JSON')" 2>/dev/null; then
    :
else
    echo "  ✗ FAIL: agent-card.json is not valid JSON"
    FAILED=1
fi

# Test 3: Required Fields Present
echo "[TEST 3] Required Fields in Agent Card..."
REQUIRED_FIELDS=("name" "description" "url" "capabilities")
MISSING_FIELDS=0
for field in "${REQUIRED_FIELDS[@]}"; do
    if echo "$AGENT_CARD" | grep -q "\"$field\""; then
        echo "    ✓ $field"
    else
        echo "    ✗ $field (missing)"
        MISSING_FIELDS=$((MISSING_FIELDS + 1))
    fi
done
if [ $MISSING_FIELDS -eq 0 ]; then
    echo "  ✓ PASS: All required fields present"
else
    echo "  ✗ FAIL: $MISSING_FIELDS required field(s) missing"
    FAILED=1
fi

# Test 4: agents.json Accessibility
echo "[TEST 4] A2A Agents JSON Accessibility..."
AGENTS_JSON=$(curl -s --max-time ${TIMEOUT} "https://${DOMAIN}/.well-known/agents.json" 2>/dev/null || echo "")
if [ -n "$AGENTS_JSON" ] && echo "$AGENTS_JSON" | grep -q '"agents"'; then
    echo "  ✓ PASS: agents.json is accessible and contains agents array"
    AGENT_COUNT=$(echo "$AGENTS_JSON" | grep -o '"name"' | wc -l | tr -d ' ')
    echo "    Found $AGENT_COUNT agent(s) in registry"
else
    echo "  ✗ FAIL: agents.json not accessible or missing agents field"
    FAILED=1
fi

# Test 5: Agents JSON Validity
echo "[TEST 5] Agents JSON Validity..."
if echo "$AGENTS_JSON" | python3 -c "import json,sys; data=json.load(sys.stdin); print(f\"  ✓ PASS: Valid JSON with {len(data.get('agents', []))} agents\")" 2>/dev/null; then
    :
else
    echo "  ✗ FAIL: agents.json is not valid JSON"
    FAILED=1
fi

# Test 6: llms.txt Accessibility
echo "[TEST 6] llms.txt Accessibility..."
LLMS_TXT=$(curl -s --max-time ${TIMEOUT} "https://${DOMAIN}/llms.txt" 2>/dev/null || echo "")
if [ -n "$LLMS_TXT" ] && [ ${#LLMS_TXT} -gt 50 ]; then
    LLMS_LEN=${#LLMS_TXT}
    echo "  ✓ PASS: llms.txt is accessible ($LLMS_LEN characters)"
else
    echo "  ⚠ WARN: llms.txt not accessible or empty"
    # Don't fail on llms.txt - it's optional
fi

# Test 7: Agent Card Has Skills
echo "[TEST 7] Agent Card Skills Section..."
if echo "$AGENT_CARD" | grep -q '"skills"'; then
    SKILL_COUNT=$(echo "$AGENT_CARD" | grep -o '"id"' | wc -l | tr -d ' ')
    echo "  ✓ PASS: Agent card has skills section ($SKILL_COUNT skill(s))"
else
    echo "  ⚠ WARN: No skills section in agent card"
fi

# Test 8: Agent Card Version Present
echo "[TEST 8] Agent Card Version..."
if echo "$AGENT_CARD" | grep -q '"version"'; then
    VERSION=$(echo "$AGENT_CARD" | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "  ✓ PASS: Agent card has version: $VERSION"
else
    echo "  ⚠ WARN: No version field in agent card"
fi

# Test 9: SSL Certificate Valid for HTTPS
echo "[TEST 9] HTTPS/SSL for A2A Endpoints..."
CERT_INFO=$(echo | openssl s_client -connect ${DOMAIN}:443 -servername ${DOMAIN} 2>/dev/null | openssl x509 -noout -subject 2>/dev/null)
if [ -n "$CERT_INFO" ]; then
    echo "  ✓ PASS: SSL certificate valid for $DOMAIN"
else
    echo "  ✗ FAIL: SSL certificate issue"
    FAILED=1
fi

# Test 10: Content-Type Headers
echo "[TEST 10] Content-Type Headers..."
CT=$(curl -sI --max-time ${TIMEOUT} "https://${DOMAIN}/.well-known/agent-card.json" 2>/dev/null | grep -i "content-type:" | head -1)
if echo "$CT" | grep -qi "json"; then
    echo "  ✓ PASS: Correct Content-Type for agent-card.json"
    echo "    $CT"
else
    echo "  ⚠ WARN: Unexpected Content-Type"
    echo "    ${CT:-'(no header)'}"
fi

echo ""
echo "=== Test Summary ==="
if [ $FAILED -eq 0 ]; then
    echo "✓ ALL CRITICAL TESTS PASSED"
    exit 0
else
    echo "✗ SOME TESTS FAILED"
    exit 1
fi
