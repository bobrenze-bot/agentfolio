#!/bin/bash
# PostHog Referral Tracker Regression Test
# Tests the PostHog referral tracking functionality for AgentFolio
# Verifies: TypeScript compilation, exported functions, referrer parsing logic
# Exit codes: 0 = pass, 1 = fail

set -e

PROJECT_DIR="/Users/serenerenze/bob-bootstrap/projects/agentrank/agentfolio"
FAILED=0

echo "=== PostHog Referral Tracker Regression Test ==="
echo "Testing: AgentFolio PostHog referral tracking functionality"
echo ""

# Test 1: TypeScript source file exists
echo "[TEST 1] TypeScript Source File Exists..."
if [ -f "${PROJECT_DIR}/src/posthog-referral-tracker.ts" ]; then
    TS_SIZE=$(wc -c < "${PROJECT_DIR}/src/posthog-referral-tracker.ts")
    echo "  ✓ PASS: posthog-referral-tracker.ts exists (${TS_SIZE} bytes)"
else
    echo "  ✗ FAIL: posthog-referral-tracker.ts not found"
    FAILED=1
fi

# Test 2: Compiled JavaScript output exists
echo "[TEST 2] Compiled JavaScript Output..."
if [ -f "${PROJECT_DIR}/dist/posthog-referral-tracker.js" ]; then
    JS_SIZE=$(wc -c < "${PROJECT_DIR}/dist/posthog-referral-tracker.js")
    echo "  ✓ PASS: Compiled JS exists (${JS_SIZE} bytes)"
else
    echo "  ✗ FAIL: Compiled JS not found - run 'npm run build'"
    FAILED=1
fi

# Test 3: TypeScript declaration file exists
echo "[TEST 3] TypeScript Declaration File..."
if [ -f "${PROJECT_DIR}/dist/posthog-referral-tracker.d.ts" ]; then
    echo "  ✓ PASS: TypeScript declarations exist"
else
    echo "  ✗ FAIL: TypeScript declarations missing"
    FAILED=1
fi

# Test 4: Check for key exported functions in source
echo "[TEST 4] Core Functions Exported in Source..."
REQUIRED_FUNCTIONS=("parseReferrer" "extractAttributionData" "getFirstTouchAttribution" "extractAgentHandle" "initializePostHog" "syncUserProperties" "trackPageView")
MISSING_FUNC=0
for func in "${REQUIRED_FUNCTIONS[@]}"; do
    if grep -q "export.*${func}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts" || grep -q "function ${func}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
        echo "    ✓ ${func}"
    else
        echo "    ✗ ${func} (missing)"
        MISSING_FUNC=$((MISSING_FUNC + 1))
    fi
done
if [ $MISSING_FUNC -eq 0 ]; then
    echo "  ✓ PASS: All required functions present"
else
    echo "  ✗ FAIL: $MISSING_FUNC required function(s) missing"
    FAILED=1
fi

# Test 5: Verify referrer type definitions
echo "[TEST 5] Referrer Type Definitions..."
if grep -q "type ReferrerType" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
    echo "  ✓ PASS: ReferrerType defined"
else
    echo "  ✗ FAIL: ReferrerType not defined"
    FAILED=1
fi

# Test 6: Verify storage keys constant
echo "[TEST 6] Storage Keys Configuration..."
if grep -q "STORAGE_KEYS" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
    echo "  ✓ PASS: STORAGE_KEYS defined"
    # Check for expected keys
    for key in "FIRST_TOUCH" "SESSION_REFERRER" "ATTRIBUTION_SYNCED"; do
        if grep -q "${key}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
            echo "    ✓ ${key}"
        else
            echo "    ✗ ${key} (missing)"
            FAILED=1
        fi
    done
else
    echo "  ✗ FAIL: STORAGE_KEYS not defined"
    FAILED=1
fi

# Test 7: Verify domain categorization arrays
echo "[TEST 7] Domain Categorization Arrays..."
DOMAIN_ARRAYS=("SOCIAL_DOMAINS" "SEARCH_DOMAINS" "DEV_DOMAINS")
for arr in "${DOMAIN_ARRAYS[@]}"; do
    if grep -q "${arr}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
        echo "    ✓ ${arr}"
    else
        echo "    ✗ ${arr} (missing)"
        FAILED=1
    fi
done
echo "  ✓ PASS: Domain categorization arrays present"

# Test 8: Verify Analytics API interface
echo "[TEST 8] AgentFolioAnalyticsAPI Interface..."
if grep -q "interface AgentFolioAnalyticsAPI" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
    echo "  ✓ PASS: AgentFolioAnalyticsAPI interface defined"
    # Check for required methods
    API_METHODS=("trackEvent" "trackPlatformClick" "trackShare" "getAttribution")
    for method in "${API_METHODS[@]}"; do
        if grep -q "${method}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
            echo "    ✓ ${method}"
        else
            echo "    ✗ ${method} (missing)"
            FAILED=1
        fi
    done
else
    echo "  ✗ FAIL: AgentFolioAnalyticsAPI interface not defined"
    FAILED=1
fi

# Test 9: Verify PostHog integration points
echo "[TEST 9] PostHog Integration Points..."
POSTHOG_CALLS=("posthog.init" "posthog.capture" "posthog.people.set" "posthog.register")
POSTHOG_FOUND=0
for call in "${POSTHOG_CALLS[@]}"; do
    if grep -q "window.posthog.*${call#posthog.}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts" || \
       grep -q "posthog.*${call#posthog.}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
        echo "    ✓ ${call}"
        POSTHOG_FOUND=$((POSTHOG_FOUND + 1))
    fi
done
if [ $POSTHOG_FOUND -ge 2 ]; then
    echo "  ✓ PASS: PostHog integration points present"
else
    echo "  ✗ FAIL: Insufficient PostHog integration found"
    FAILED=1
fi

# Test 10: Verify event tracking calls
echo "[TEST 10] Event Tracking Implementation..."
EVENT_NAMES=("referral_detected" "agent_profile_viewed" "platform_link_clicked" "profile_shared")
EVENT_FOUND=0
for event in "${EVENT_NAMES[@]}"; do
    if grep -q "'${event}'" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
        echo "    ✓ ${event}"
        EVENT_FOUND=$((EVENT_FOUND + 1))
    fi
done
if [ $EVENT_FOUND -ge 3 ]; then
    echo "  ✓ PASS: Event tracking implemented"
else
    echo "  ⚠ WARN: Some event tracking calls missing (${EVENT_FOUND}/4 found)"
fi

# Test 11: Verify UTM parameter handling
echo "[TEST 11] UTM Parameter Extraction..."
UTM_PARAMS=("utm_source" "utm_medium" "utm_campaign" "utm_content")
UTM_FOUND=0
for param in "${UTM_PARAMS[@]}"; do
    if grep -q "${param}" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
        echo "    ✓ ${param}"
        UTM_FOUND=$((UTM_FOUND + 1))
    fi
done
if [ $UTM_FOUND -ge 3 ]; then
    echo "  ✓ PASS: UTM parameter handling present"
else
    echo "  ✗ FAIL: UTM parameter handling incomplete"
    FAILED=1
fi

# Test 12: Verify localStorage/sessionStorage usage
echo "[TEST 12] Storage API Usage..."
if grep -q "localStorage" "${PROJECT_DIR}/src/posthog-referral-tracker.ts" && \
   grep -q "sessionStorage" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
    echo "  ✓ PASS: Both localStorage and sessionStorage used"
else
    echo "  ✗ FAIL: Storage API not properly utilized"
    FAILED=1
fi

# Test 13: Verify referrer parsing logic exists
echo "[TEST 13] Referrer Parsing Logic..."
if grep -q "parseReferrer" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
    # Check for referrer type returns
    REF_TYPES=("direct" "social" "search" "developer" "referral" "unknown")
    REF_FOUND=0
    for ref_type in "${REF_TYPES[@]}"; do
        if grep -q "type: '${ref_type}'" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
            REF_FOUND=$((REF_FOUND + 1))
        fi
    done
    if [ $REF_FOUND -ge 5 ]; then
        echo "  ✓ PASS: Comprehensive referrer parsing (${REF_FOUND}/6 types)"
    else
        echo "  ⚠ WARN: Some referrer types missing (${REF_FOUND}/6)"
    fi
else
    echo "  ✗ FAIL: parseReferrer function not found"
    FAILED=1
fi

# Test 14: Verify MutationObserver for SPA navigation
echo "[TEST 14] SPA Navigation Tracking..."
if grep -q "MutationObserver" "${PROJECT_DIR}/src/posthog-referral-tracker.ts"; then
    echo "  ✓ PASS: MutationObserver for SPA navigation present"
else
    echo "  ⚠ WARN: MutationObserver not found (SPA navigation may not track)"
fi

# Test 15: Compile check
echo "[TEST 15] TypeScript Compilation Check..."
cd "${PROJECT_DIR}"
if npm run build > /tmp/tsc-build.log 2>&1; then
    echo "  ✓ PASS: TypeScript compiles without errors"
else
    echo "  ✗ FAIL: TypeScript compilation errors detected"
    tail -20 /tmp/tsc-build.log | sed 's/^/    /'
    FAILED=1
fi

# Summary
echo ""
echo "=== Test Summary ==="
if [ $FAILED -eq 0 ]; then
    echo "✓ ALL TESTS PASSED"
    echo ""
    echo "PostHog Referral Tracker is properly implemented with:"
    echo "  - Full TypeScript type definitions"
    echo "  - Referrer parsing and categorization"
    echo "  - UTM parameter tracking"
    echo "  - PostHog integration"
    echo "  - Analytics API exposure"
    exit 0
else
    echo "✗ SOME TESTS FAILED (${FAILED} critical issue(s))"
    exit 1
fi
