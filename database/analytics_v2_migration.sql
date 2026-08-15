-- ORBIDENSE AI Analytics V2 / Observability
-- Safe to run multiple times. The Python initializer creates the same objects.

CREATE TABLE IF NOT EXISTS analytics_errors (
    error_id BIGSERIAL PRIMARY KEY, session_id TEXT, page_name TEXT,
    component TEXT NOT NULL, operation TEXT, severity TEXT NOT NULL DEFAULT 'error',
    error_type TEXT NOT NULL, error_hash TEXT NOT NULL, message_redacted TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_errors_recorded_at ON analytics_errors(recorded_at);
CREATE INDEX IF NOT EXISTS idx_analytics_errors_component ON analytics_errors(component);
CREATE INDEX IF NOT EXISTS idx_analytics_errors_hash ON analytics_errors(error_hash);

CREATE TABLE IF NOT EXISTS analytics_performance (
    performance_id BIGSERIAL PRIMARY KEY, session_id TEXT, page_name TEXT,
    operation TEXT NOT NULL, duration_ms DOUBLE PRECISION NOT NULL, success BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_performance_recorded_at ON analytics_performance(recorded_at);
CREATE INDEX IF NOT EXISTS idx_analytics_performance_operation ON analytics_performance(operation);

CREATE TABLE IF NOT EXISTS analytics_ai_usage (
    ai_usage_id BIGSERIAL PRIMARY KEY, session_id TEXT, page_name TEXT, request_category TEXT, model_name TEXT,
    duration_ms DOUBLE PRECISION, success BOOLEAN NOT NULL DEFAULT TRUE, input_chars INTEGER, output_chars INTEGER,
    error_type TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb, recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_ai_usage_recorded_at ON analytics_ai_usage(recorded_at);

CREATE TABLE IF NOT EXISTS analytics_data_quality (
    quality_id BIGSERIAL PRIMARY KEY, source_name TEXT NOT NULL, check_name TEXT NOT NULL, status TEXT NOT NULL,
    affected_records BIGINT, freshness_seconds BIGINT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_data_quality_recorded_at ON analytics_data_quality(recorded_at);
