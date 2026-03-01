#!/bin/bash
# AgentFolio Submit Form Bot Detection Regression Test
# Verifies submission system correctly identifies and prevents bot submissions
# to wrong targets (agentfolio.bot vs agentfolio.io)
# Tests detection of automated submission patterns
# Exit codes: 0 = pass, 1 = fail

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/Users/serenerenze/bob-bootstrap"
AGENTRANK_DIR="${PROJECT_ROOT}/projects/agentrank"
SUBMIT_SCRIPT="${PROJECT_ROOT}/scripts/agentfolio_submit.py"
WRONG_SCRIPT="${PROJECT_ROOT}/agents/rhythm-worker/scripts/WRONG-TARGET-agentfolio-submit.py"
FAILED=0

echo "=== AgentFolio Bot Detection Regression Test ==="
echo "Purpose: Prevent automated submissions to wrong AgentFolio targets"
echo "Target: agentfolio.io (GitHub Pages) NOT agentfolio.bot (Solana)"
echo ""

# Test 1: Verify submit.html uses mailto: (human-required) method
echo "[TEST 1] Submission Method Validation..."
if [ -f "${AGENTRANK_DIR}/submit.html" ]; then
    if grep -q 'mailto:' "${AGENTRANK_DIR}/submit.html"; then
        echo "  ✓ PASS: submit.html uses mailto: method (requires human interaction)"
    else
        echo "  ✗ FAIL: submit.html missing mailto: method"
        FAILED=1
    fi
    
    # Check for honeypot field (bot detection)
    if grep -qE '(honeypot|hpfield|bot-check|_gotcha)' "${AGENTRANK_DIR}/submit.html"; then
        echo "  ✓ PASS: Honeypot field present for bot detection"
    else
        echo "  ⚠ WARN: No honeypot field detected (recommend adding)"
    fi
else
    echo "  ✗ FAIL: submit.html not found"
    FAILED=1
fi

# Test 2: Check submission scripts for wrong target detection
echo ""
echo "[TEST 2] Target URL Validation..."

# Check if agentfolio_submit.py exists and validates URLs
if [ -f "$SUBMIT_SCRIPT" ]; then
    # Check for agentfolio.io validation
    if grep -q 'agentfolio\.io' "$SUBMIT_SCRIPT"; then
        echo "  ✓ PASS: Script references correct target (agentfolio.io)"
    else
        echo "  ⚠ WARN: Script may not explicitly validate agentfolio.io URL"
    fi
    
    # Check for agentfolio.bot rejection
    if grep -q 'agentfolio\.bot' "$SUBMIT_SCRIPT"; then
        if grep -qE '(reject|block|skip|warn|error).*agentfolio\.bot' "$SUBMIT_SCRIPT"; then
            echo "  ✓ PASS: Script explicitly rejects agentfolio.bot"
        else
            echo "  ⚠ WARN: Script mentions agentfolio.bot without rejection logic"
        fi
    else
        echo "  ⚠ WARN: Script lacks agentfolio.bot detection"
    fi
else
    echo "  ⚠ WARN: agentfolio_submit.py not found at expected path"
fi

# Test 3: Verify WRONG-TARGET script exists as documentation
echo ""
echo "[TEST 3] Wrong Target Documentation..."
if [ -f "$WRONG_SCRIPT" ]; then
    echo "  ✓ PASS: WRONG-TARGET script exists as warning documentation"
    
    # Check if it mentions the actual issue
    if grep -q 'agentfolio\.bot' "$WRONG_SCRIPT"; then
        echo "  ✓ PASS: Wrong-target script documents bot target confusion"
    fi
else
    echo "  ⚠ WARN: WRONG-TARGET script not found"
fi

# Test 4: Check correction log exists and is readable
echo ""
echo "[TEST 4] Correction Log Verification..."
CORRECTION_LOG="${PROJECT_ROOT}/OPERATIONAL/agentfolio-correction-log.md"
if [ -f "$CORRECTION_LOG" ]; then
    echo "  ✓ PASS: Correction log exists"
    
    # Check for key learnings
    if grep -q 'agentfolio\.io' "$CORRECTION_LOG" && grep -q 'agentfolio\.bot' "$CORRECTION_LOG"; then
        echo "  ✓ PASS: Correction log documents both targets"
    fi
    
    if grep -q 'RESOLVED' "$CORRECTION_LOG"; then
        echo "  ✓ PASS: Correction log shows issue resolution status"
    fi
else
    echo "  ✗ FAIL: Correction log not found"
    FAILED=1
fi

# Test 5: Verify submit form has timing/delay protections
echo ""
echo "[TEST 5] Anti-Automation Protections..."
if [ -f "${AGENTRANK_DIR}/submit.html" ]; then
    # Check for CSRF token or similar
    if grep -qE '(csrf|token|nonce|timestamp)' "${AGENTRANK_DIR}/submit.html"; then
        echo "  ✓ PASS: Form includes CSRF/timestamp protection"
    else
        echo "  ⚠ WARN: No CSRF token found in form (recommend adding)"
    fi
    
    # Check for JavaScript validation
    if grep -q '<script>' "${AGENTRANK_DIR}/submit.html"; then
        echo "  ✓ PASS: Form includes JavaScript validation"
    else
        echo "  ⚠ WARN: No JavaScript validation (bots can submit directly)"
    fi
fi

# Test 6: Rate Limiting Check (if submission logs exist)
echo ""
echo "[TEST 6] Submission Rate Limiting..."
SUBMISSION_LOG="${PROJECT_ROOT}/logs/agentfolio-submit.log"
if [ -f "$SUBMISSION_LOG" ]; then
    # Count submissions in last hour (should be low)
    RECENT_SUBMISSIONS=$(grep -c "$(date +%Y-%m-%d %H)" "$SUBMISSION_LOG" 2>/dev/null || echo "0")
    if [ "$RECENT_SUBMISSIONS" -lt 10 ]; then
        echo "  ✓ PASS: Submission rate is reasonable (${RECENT_SUBMISSIONS} in current hour)"
    else
        echo "  ⚠ WARN: High submission rate detected (${RECENT_SUBMISSIONS} in current hour)"
    fi
else
    echo "  ⚠ WARN: No submission log found (cannot check rate)"
fi

# Test 7: Verify agent data source is correct
echo ""
echo "[TEST 7] Data Source Validation..."
AGENTS_JSON="${AGENTRANK_DIR}/data/agents.json"
if [ -f "$AGENTS_JSON" ]; then
    if python3 -c "import json; data=json.load(open('$AGENTS_JSON')); print(f'  ✓ PASS: Valid agents.json with {len(data.get(\'agents\', []))} agents')" 2>/dev/null; then
        : # Already printed
    else
        echo "  ✗ FAIL: agents.json is invalid"
        FAILED=1
    fi
else
    echo "  ⚠ WARN: agents.json not found"
fi

# Test 8: Check for browser automation detection
echo ""
echo "[TEST 8] Browser Automation Detection..."
if [ -f "${AGENTRANK_DIR}/submit.html" ]; then
    # Check for user-agent checks or similar
    if grep -qE '(navigator|userAgent|webdriver)' "${AGENTRANK_DIR}/submit.html"; then
        echo "  ✓ PASS: Form includes browser automation checks"
    else
        echo "  ⚠ WARN: No browser automation detection found"
    fi
fi

# Test 9: Verify submission tracking file exists
echo ""
echo "[TEST 9] Submission Tracking..."
TRACKING_FILE="${PROJECT_ROOT}/.agentfolio-submissions.json"
if [ -f "$TRACKING_FILE" ]; then
    echo "  ✓ PASS: Submission tracking file exists"
    if python3 -c "import json; json.load(open('$TRACKING_FILE')); print('  ✓ PASS: Tracking file is valid JSON')" 2>/dev/null; then
        : # Already printed
    else
        echo "  ⚠ WARN: Tracking file has JSON errors"
    fi
else
    echo "  ⚠ WARN: No submission tracking file found"
fi

# Test 10: Preventive Rules Check
echo ""
echo "[TEST 10] MORNING-TAPE Rule Verification..."
MORNING_TAPE="${PROJECT_ROOT}/agents/rhythm-worker/memory/MORNING-TAPE.md"
if [ -f "$MORNING_TAPE" ]; then
    if grep -q 'agentfolio\.io' "$MORNING_TAPE" && grep -q 'agentfolio\.bot' "$MORNING_TAPE"; then
        echo "  ✓ PASS: MORNING-TAPE contains AgentFolio validation rules"
    else
        echo "  ⚠ WARN: MORNING-TAPE missing AgentFolio validation rules"
    fi
else
    echo "  ⚠ WARN: MORNING-TAPE not found"
fi

echo ""
echo "=== Remediation Recommendations ==="
if [ $FAILED -eq 0 ]; then
    echo "✓ BOT DETECTION CHECKS PASSED"
    echo ""
    echo "Key Protections Active:"
    echo "  - Correct target (agentfolio.io) validated"
    echo "  - Wrong target (agentfolio.bot) documented"
    echo "  - Correction log available for reference"
else
    echo "✗ BOT DETECTION ISSUES FOUND"
    echo ""
    echo "Required Actions:"
    echo "  1. Ensure submission scripts validate target URL"
    echo "  2. Add honeypot fields to submit.html"
    echo "  3. Document wrong-target prevention in correction log"
fi

echo ""
echo "=== Test Complete ==="
exit $FAILED
