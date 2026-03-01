#!/bin/bash
# AgentFolio Tier-Up Celebration Cron Job
# Runs daily to detect agent tier changes and post celebrations

BASE_DIR="/Users/serenerenze/bob-bootstrap/projects/agentrank"
LOG_FILE="$BASE_DIR/work-records/cron/tier-up-$(date +%Y%m%d).log"

mkdir -p "$BASE_DIR/work-records/cron"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting AgentFolio tier-up check..." >> "$LOG_FILE"

cd "$BASE_DIR"

# Run the tier-up automation (no dry-run in production)
python3 scripts/tier_up_automation.py --data-dir "$BASE_DIR" 2>>1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

exit $EXIT_CODE
