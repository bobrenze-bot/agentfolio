#!/bin/bash
# AgentFolio Agent of the Week - Weekly Rotation Cron
# Runs every Monday at 9:00 AM PST
# Schedule: 0 9 * * 1

set -e

SCRIPT_DIR="/Users/serenerenze/bob-bootstrap/projects/agentrank/scripts"
DATA_DIR="/Users/serenerenze/bob-bootstrap/projects/agentrank/data"
LOG_FILE="/Users/serenerenze/bob-bootstrap/logs/agent-of-week.log"

# Create log directory if needed
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Agent of the Week Rotation Starting ==="

# Check if rotation is needed
cd "$SCRIPT_DIR"

if python3 agent_of_week.py --check; then
    log "Rotation needed. Selecting new Agent of the Week..."
    
    # Select next agent
    if python3 agent_of_week.py --select; then
        log "✓ New Agent of the Week selected successfully"
        
        # Regenerate the site to include the new featured agent
        log "Regenerating AgentFolio site..."
        if python3 generate_site.py; then
            log "✓ Site regenerated successfully"
            
            # Commit changes to git
            cd /Users/serenerenze/bob-bootstrap/projects/agentrank
            git add data/agent_of_week.json index.html
            git commit -m "Agent of the Week rotation - $(date '+%Y-%m-%d')" || true
            git push origin main || log "Warning: Could not push to remote"
            
            log "✓ Agent of the Week rotation complete"
        else
            log "ERROR: Site generation failed"
            exit 1
        fi
    else
        log "ERROR: Failed to select new Agent of the Week"
        exit 1
    fi
else
    log "No rotation needed. Current Agent of the Week still active."
fi

log "=== Agent of the Week Cron Complete ==="
