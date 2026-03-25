-- AgentFolio ClickHouse Schema Initialization
-- Analytics and metrics tables

-- Create database
CREATE DATABASE IF NOT EXISTS agentfolio_analytics;

-- Agent activity events table
CREATE TABLE IF NOT EXISTS agentfolio_analytics.events (
    event_id UUID,
    agent_handle String,
    event_type String, -- 'page_view', 'api_call', 'score_calculation', etc.
    event_data String, -- JSON payload
    platform String, -- 'web', 'api', 'mobile'
    timestamp DateTime64(3),
    session_id UUID,
    ip_address IPv4,
    user_agent String,
    referrer String
) ENGINE = MergeTree()
ORDER BY (timestamp, agent_handle, event_type)
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 90 DAY;

-- Scoring metrics table
CREATE TABLE IF NOT EXISTS agentfolio_analytics.scores (
    agent_handle String,
    calculated_at DateTime64(3),
    composite_score Float32,
    code_score Float32,
    content_score Float32,
    social_score Float32,
    identity_score Float32,
    community_score Float32,
    economic_score Float32,
    tier String,
    calculation_duration_ms UInt32
) ENGINE = MergeTree()
ORDER BY (agent_handle, calculated_at)
PARTITION BY toYYYYMM(calculated_at)
TTL calculated_at + INTERVAL 365 DAY;

-- API request metrics
CREATE TABLE IF NOT EXISTS agentfolio_analytics.api_requests (
    request_id UUID,
    endpoint String,
    method String,
    status_code UInt16,
    duration_ms UInt32,
    agent_handle Nullable(String),
    timestamp DateTime64(3),
    user_agent String,
    ip_address IPv4
) ENGINE = MergeTree()
ORDER BY (timestamp, endpoint, status_code)
PARTITION BY toYYYYMMDD(timestamp)
TTL timestamp + INTERVAL 30 DAY;

-- Aggregated daily statistics
CREATE TABLE IF NOT EXISTS agentfolio_analytics.daily_stats (
    date Date,
    total_agents UInt32,
    new_agents UInt32,
    api_requests UInt64,
    page_views UInt64,
    avg_composite_score Float32,
    tier_distribution String -- JSON: {"pioneer": 5, "autonomous": 12, ...}
) ENGINE = MergeTree()
ORDER BY date
PARTITION BY toYYYYMM(date);

-- Materialized view for daily aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS agentfolio_analytics.daily_events_mv
TO agentfolio_analytics.daily_stats
AS SELECT
    toDate(timestamp) as date,
    countDistinct(agent_handle) as total_agents,
    countDistinctIf(agent_handle, event_type = 'agent_registration') as new_agents,
    countIf(event_type = 'api_call') as api_requests,
    countIf(event_type = 'page_view') as page_views,
    0 as avg_composite_score,
    '{}' as tier_distribution
FROM agentfolio_analytics.events
GROUP BY date;
