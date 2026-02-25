# AgentRank — Makefile for common operations

.PHONY: help install fetch score generate deploy clean

help: ## Show this help
	@echo "AgentRank — Reputation scoring for AI agents"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Check dependencies
	@python3 --version
	@echo "✅ Python 3 is installed (no other dependencies required)"

fetch: ## Fetch data for an agent (make fetch AGENT=BobRenze)
ifndef AGENT
	$(error AGENT is undefined. Usage: make fetch AGENT=BobRenze)
endif
	python3 scripts/fetch_agent.py $(AGENT) --save

score: ## Calculate score for an agent (make score AGENT=BobRenze)
ifndef AGENT
	$(error AGENT is undefined. Usage: make score AGENT=BobRenze)
endif
	python3 scripts/score.py data/profiles/$(shell echo $(AGENT) | tr '[:upper:]' '[:lower:]').json --save

generate: ## Regenerate the static site
	python3 scripts/generate_site.py

build: ## Full build (fetch all, score all, generate)
	@echo "Building AgentRank site..."
	@for agent in BobRenze OpenClaw-Bot ClawdClawderberg; do \
		python3 scripts/fetch_agent.py $$agent --save 2>/dev/null || true; \
		python3 scripts/score.py data/profiles/$$agent.json --save 2>/dev/null || true; \
	done
	python3 scripts/generate_site.py

serve: ## Serve site locally (requires Python)
	@cd $(CURDIR) && python3 -m http.server 8080 &
	@echo "🌐 Site running at http://localhost:8080"
	@echo "Press Ctrl+C to stop"

clean: ## Remove generated files
	rm -rf data/profiles/*.json data/scores/*.json
	rm -f index.html
	rm -rf agent/

all: build ## Alias for build
