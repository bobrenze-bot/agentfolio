#!/bin/bash

# AgentFolio Phase 1 - One-Click Docker Install
# Usage: ./install.sh [domain]
# Example: ./install.sh agentfolio.io

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="${1:-agentfolio.io}"
EMAIL=""
USE_LETSENCRYPT=false
SSL_TYPE="self-signed"

# Print banner
print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    _             _       _  _         _       _
   / \   ___  ___| |_   _| || |_  ___ | | ___ | |_
  / _ \ / _ \/ __| __| |_  ..  _|/ _ \| |/ _ \| __|
 / ___ \  __/\__ \ |_  |_      _| (_) | | (_) | |_
/_/   \_\___||___/\__|   |_||_|  \___/|_|\___/ \__|

    Production Docker Setup - Phase 1
EOF
    echo -e "${NC}"
    echo
}

# Print status messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Prompt user for configuration
prompt_config() {
    info "Configuration Setup"
    echo "=================="
    
    # Domain
    read -p "Enter your domain (default: $DOMAIN): " input_domain
    DOMAIN="${input_domain:-$DOMAIN}"
    
    # SSL Certificate type
    echo
    echo "SSL Certificate Options:"
    echo "  1) Let's Encrypt (recommended for production, requires port 80/443)"
    echo "  2) Self-signed certificate (for testing/development)"
    echo "  3) Use existing certificate"
    read -p "Select option (1-3, default: 1): " ssl_choice
    ssl_choice="${ssl_choice:-1}"
    
    case $ssl_choice in
        1)
            SSL_TYPE="letsencrypt"
            USE_LETSENCRYPT=true
            read -p "Enter your email for Let's Encrypt notifications: " EMAIL
            if [[ ! "$EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
                warn "Invalid email format. Let's Encrypt will still work but you won't get expiry notifications."
            fi
            ;;
        2)
            SSL_TYPE="self-signed"
            USE_LETSENCRYPT=false
            ;;
        3)
            SSL_TYPE="existing"
            USE_LETSENCRYPT=false
            warn "Please ensure your certificates are placed in nginx/ssl/ directory before starting"
            read -p "Press Enter to continue..."
            ;;
        *)
            error "Invalid choice"
            exit 1
            ;;
    esac
    
    # Confirm settings
    echo
    echo "Configuration Summary:"
    echo "  Domain: $DOMAIN"
    echo "  SSL Type: $SSL_TYPE"
    if [ -n "$EMAIL" ]; then
        echo "  Email: $EMAIL"
    fi
    read -p "Is this correct? (Y/n): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$|^$ ]]; then
        echo "Aborted."
        exit 0
    fi
}

# Generate .env file
generate_env() {
    info "Generating environment configuration..."
    
    # Generate secure secrets
    POSTGRES_PASSWORD=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '=' | cut -c1-32)
    CLICKHOUSE_PASSWORD=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '=' | cut -c1-32)
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n')
    
    cat > "$SCRIPT_DIR/.env" << EOF
# AgentFolio Environment Configuration
# Generated on $(date)

# Application
APP_ENV=production
DEBUG=false
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN,*.${DOMAIN},api.${DOMAIN}
CORS_ORIGINS=https://$DOMAIN,https://*.${DOMAIN},https://api.${DOMAIN}

# Database
POSTGRES_USER=agentfolio
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=agentfolio
POSTGRES_PORT=5432

# Redis
REDIS_PORT=6379

# ClickHouse
CLICKHOUSE_USER=agentfolio
CLICKHOUSE_PASSWORD=$CLICKHOUSE_PASSWORD
CLICKHOUSE_DB=agentfolio_analytics
CLICKHOUSE_HTTP_PORT=8123
CLICKHOUSE_NATIVE_PORT=9000

# Ports
APP_PORT=8000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
FLOWER_PORT=5555
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Celery
CELERY_CONCURRENCY=4

# Monitoring
FLOWER_BASIC_AUTH=admin:$(openssl rand -base64 12 2>/dev/null || head -c 12 /dev/urandom | base64 | tr -d '=' | cut -c1-12)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 12 2>/dev/null || head -c 12 /dev/urandom | base64 | tr -d '=' | cut -c1-12)
GRAFANA_ROOT_URL=https://grafana.${DOMAIN}

# SSL
SSL_CERTIFICATE=/etc/nginx/ssl/cert.pem
SSL_CERTIFICATE_KEY=/etc/nginx/ssl/key.pem

# External (Add your own)
GITHUB_TOKEN=your-github-token
MOLTBOOK_API_KEY=your-moltbook-api-key
TOKU_API_KEY=your-toku-api-key

# Scoring
SCORING_INTERVAL_HOURS=24
AGENT_OF_WEEK_DAY=1
AGENT_OF_WEEK_HOUR=9
EOF
    
    success "Created .env file with secure secrets"
    
    # Save credentials for user
    cat > "$SCRIPT_DIR/.credentials" << EOF
# AgentFolio Admin Credentials
# Generated on $(date)
# Keep this file secure!

Database:
  User: agentfolio
  Password: $POSTGRES_PASSWORD

ClickHouse:
  User: agentfolio
  Password: $CLICKHOUSE_PASSWORD

Grafana:
  User: admin
  Password: (see .env file)

Flower:
  User: admin
  Password: (see .env file)

Secret Key: $SECRET_KEY (keep this secure!)

URLs:
  Main App: https://$DOMAIN
  API: https://api.${DOMAIN}
  Grafana: https://grafana.${DOMAIN} (if configured)
  Flower: http://localhost:5555 (internal only)
EOF
    
    chmod 600 "$SCRIPT_DIR/.credentials"
    success "Saved credentials to .credentials (secure permissions set)"
}

# Setup SSL certificates
setup_ssl() {
    info "Setting up SSL certificates..."
    
    mkdir -p "$SCRIPT_DIR/nginx/ssl"
    
    case $SSL_TYPE in
        self-signed)
            info "Generating self-signed certificate..."
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout "$SCRIPT_DIR/nginx/ssl/key.pem" \
                -out "$SCRIPT_DIR/nginx/ssl/cert.pem" \
                -subj "/C=US/ST=State/L=City/O=AgentFolio/CN=$DOMAIN" \
                -addext "subjectAltName=DNS:$DOMAIN,DNS:*.$DOMAIN,DNS:localhost,IP:127.0.0.1"
            chmod 600 "$SCRIPT_DIR/nginx/ssl/key.pem"
            success "Self-signed certificate generated (valid for 365 days)"
            warn "Browsers will show a security warning. Use Let's Encrypt for production."
            ;;
            
        letsencrypt)
            info "Let's Encrypt certificates will be generated on first run"
            info "Ensure ports 80 and 443 are accessible from the internet"
            ;;
            
        existing)
            if [ ! -f "$SCRIPT_DIR/nginx/ssl/cert.pem" ] || [ ! -f "$SCRIPT_DIR/nginx/ssl/key.pem" ]; then
                error "Existing certificates not found in nginx/ssl/"
                error "Please place your certificate files as:"
                error "  - nginx/ssl/cert.pem"
                error "  - nginx/ssl/key.pem"
                exit 1
            fi
            success "Using existing certificates"
            ;;
    esac
}

# Create directory structure
create_directories() {
    info "Creating directory structure..."
    
    mkdir -p "$SCRIPT_DIR"/{nginx/conf.d,nginx/ssl,clickhouse/init,clickhouse,init-scripts,monitoring/{prometheus,grafana/{dashboards,datasources}},logs}
    
    success "Directory structure created"
}

# Pull Docker images
pull_images() {
    info "Pulling Docker images..."
    
    cd "$SCRIPT_DIR"
    docker compose pull
    
    success "All images pulled"
}

# Start services
start_services() {
    info "Starting AgentFolio services..."
    
    cd "$SCRIPT_DIR"
    
    # Start databases first
    info "Starting databases..."
    docker compose up -d postgres redis clickhouse
    
    # Wait for databases to be healthy
    info "Waiting for databases to be ready..."
    sleep 10
    
    # Start the rest
    info "Starting application services..."
    docker compose up -d app celery-worker celery-scheduler nginx
    
    success "All services started"
}

# Print final instructions
print_instructions() {
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        AgentFolio Installation Complete!               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Access your application:"
    
    if [ "$SSL_TYPE" = "self-signed" ]; then
        echo "  ⚠️  NOTE: Using self-signed certificate (browser warnings expected)"
        echo "  Main App: https://$DOMAIN (accept the security warning)"
    else
        echo "  Main App: https://$DOMAIN"
    fi
    
    echo "  API: https://api.${DOMAIN}"
    echo "  Health Check: https://${DOMAIN}/health"
    echo
    echo "Management:"
    echo "  View logs: docker compose logs -f"
    echo "  Stop: docker compose down"
    echo "  Restart: docker compose restart"
    echo
    echo "Credentials saved in: .credentials (keep secure!)"
    echo
    
    if [ "$USE_LETSENCRYPT" = true ]; then
        echo -e "${YELLOW}Next Steps for Let's Encrypt:${NC}"
        echo "1. Ensure DNS points to this server: $DOMAIN -> $(curl -s icanhazip.com)"
        echo "2. Ports 80 and 443 must be open to the internet"
        echo "3. Run: ./scripts/setup-letsencrypt.sh $DOMAIN $EMAIL"
        echo
    fi
    
    echo -e "${BLUE}Need help? Visit: https://docs.agentfolio.io${NC}"
    echo
}

# Main execution
main() {
    print_banner
    check_prerequisites
    prompt_config
    create_directories
    generate_env
    setup_ssl
    pull_images
    start_services
    print_instructions
}

# Handle command line arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "AgentFolio Docker Installer"
    echo
    echo "Usage: ./install.sh [domain]"
    echo
    echo "Examples:"
    echo "  ./install.sh                  # Use default domain (agentfolio.io)"
    echo "  ./install.sh mydomain.com     # Use custom domain"
    echo
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo
    exit 0
fi

# Run main function
main
