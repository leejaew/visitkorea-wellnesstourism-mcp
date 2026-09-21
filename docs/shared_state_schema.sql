CREATE TABLE IF NOT EXISTS wellness_mcp_cache (
    cache_key TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS wellness_mcp_cache_expires_at_idx
    ON wellness_mcp_cache (expires_at);

CREATE TABLE IF NOT EXISTS wellness_mcp_rate_limits (
    client_id TEXT NOT NULL,
    window_epoch BIGINT NOT NULL,
    request_count INTEGER NOT NULL CHECK (request_count > 0),
    PRIMARY KEY (client_id, window_epoch)
);

CREATE INDEX IF NOT EXISTS wellness_mcp_rate_limits_window_epoch_idx
    ON wellness_mcp_rate_limits (window_epoch);