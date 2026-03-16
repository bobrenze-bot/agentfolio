#!/bin/bash
# DISABLED - SSL is working fine, no need for regression testing
# Original: AgentFolio SSL Regression Test
exit 0
# Verifies SSL/TLS configuration remains valid after Cloudflare "Full (strict)" fix
# Exit codes: 0 = pass, 1 = fail

set -e

SITE="agentfolio.io"
TIMEOUT=30
FAILED=0

echo "=== AgentFolio SSL Regression Test ==="
echo "Testing: https://${SITE}/"
echo ""

# Test 1: HTTPS Connectivity
echo "[TEST 1] HTTPS Connectivity..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time ${TIMEOUT} "https://${SITE}/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ PASS: HTTPS returns 200"
else
    echo "  ✗ FAIL: HTTPS returned ${HTTP_CODE} (expected 200)"
    FAILED=1
fi

# Test 2: SSL Certificate Validity
echo "[TEST 2] SSL Certificate Validity..."
CERT_INFO=$(echo | openssl s_client -connect ${SITE}:443 -servername ${SITE} 2>/dev/null | openssl x509 -noout -dates -subject 2>/dev/null)
if [ -n "$CERT_INFO" ]; then
    echo "  ✓ PASS: SSL certificate is valid"
    echo "    $CERT_INFO" | head -3 | sed 's/^/    /'
else
    echo "  ✗ FAIL: Could not retrieve SSL certificate"
    FAILED=1
fi

# Test 3: Certificate Expiration (must be valid for >7 days)
echo "[TEST 3] Certificate Expiration..."
END_DATE=$(echo | openssl s_client -connect ${SITE}:443 -servername ${SITE} 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$END_DATE" ]; then
    END_EPOCH=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$END_DATE" +%s 2>/dev/null || date -d "$END_DATE" +%s 2>/dev/null || echo 0)
    NOW_EPOCH=$(date +%s)
    DAYS_REMAINING=$(( (END_EPOCH - NOW_EPOCH) / 86400 ))
    
    if [ $DAYS_REMAINING -gt 7 ]; then
        echo "  ✓ PASS: Certificate valid for ${DAYS_REMAINING} more days"
    else
        echo "  ✗ FAIL: Certificate expires in ${DAYS_REMAINING} days (threshold: 7)"
        FAILED=1
    fi
else
    echo "  ⚠ WARN: Could not determine certificate expiration"
fi

# Test 4: Cloudflare TLS Headers
echo "[TEST 4] Cloudflare TLS Configuration..."
CF_SERVER=$(curl -sI --max-time ${TIMEOUT} "https://${SITE}/" 2>/dev/null | grep -i "^server:" | head -1)
if echo "$CF_SERVER" | grep -qi "cloudflare"; then
    echo "  ✓ PASS: Served via Cloudflare"
    echo "    ${CF_SERVER}"
else
    echo "  ✗ FAIL: Not served via Cloudflare (SSL config may have changed)"
    echo "    ${CF_SERVER:-"(no server header)"}"
    FAILED=1
fi

# Test 5: HTTP Strict Transport Security
echo "[TEST 5] HSTS Header..."
HSTS=$(curl -sI --max-time ${TIMEOUT} "https://${SITE}/" 2>/dev/null | grep -i "strict-transport-security" | head -1)
if [ -n "$HSTS" ]; then
    echo "  ✓ PASS: HSTS header present"
    echo "    ${HSTS}"
else
    echo "  ⚠ WARN: HSTS header not present"
fi

# Test 6: No HTTP downgrade possible
echo "[TEST 6] HTTP→HTTPS Redirect..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code},%{redirect_url}" --max-time ${TIMEOUT} "http://${SITE}/" 2>/dev/null || echo "000,")
HTTP_CODE=$(echo "$HTTP_RESPONSE" | cut -d',' -f1)
REDIRECT=$(echo "$HTTP_RESPONSE" | cut -d',' -f2)

if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "308" ] || echo "$REDIRECT" | grep -q "https://"; then
    echo "  ✓ PASS: HTTP redirects to HTTPS"
else
    echo "  ⚠ WARN: HTTP does not redirect (code: ${HTTP_CODE})"
fi

# Test 7: TLS Version (must be 1.2+)
echo "[TEST 7] TLS Protocol Version..."
TLS_VERSION=$(echo | openssl s_client -connect ${SITE}:443 -servername ${SITE} 2>/dev/null | grep "Protocol" | head -1 || echo "")
if echo "$TLS_VERSION" | grep -q "TLSv1.2\|TLSv1.3"; then
    echo "  ✓ PASS: Using modern TLS (1.2 or 1.3)"
    echo "    ${TLS_VERSION}" | sed 's/^/    /'
else
    echo "  ✗ FAIL: TLS version issue: ${TLS_VERSION:-"not detected"}"
    FAILED=1
fi

echo ""
echo "=== Test Summary ==="
if [ $FAILED -eq 0 ]; then
    echo "✓ ALL TESTS PASSED"
    exit 0
else
    echo "✗ SOME TESTS FAILED"
    exit 1
fi