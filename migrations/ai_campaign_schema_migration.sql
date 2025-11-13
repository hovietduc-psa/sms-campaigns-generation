-- AI Campaign Generation Database Schema Migration
-- Version: 2.0 - AI Campaign Tables
-- Description: Complete schema for AI SMS Campaign Generation System with ai_ prefixed tables
-- Compatible with PostgreSQL 13+
-- This migration creates all necessary tables for AI campaign logging and metrics

-- ============================================================================
-- AI CAMPAIGN LOGS TABLE
-- Stores individual AI campaign generation requests and their results
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_campaign_logs (
    -- Primary identifier
    id TEXT(255) NOT NULL PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Campaign identification
    campaign_id VARCHAR(255) NOT NULL,

    -- Generation status
    status VARCHAR(50) NOT NULL,

    -- Campaign details
    campaignDescription TEXT NOT NULL,
    errorMessage TEXT NULL,

    -- Generated campaign flow (JSON)
    generatedFlow JSONB NOT NULL,

    -- Performance metrics
    generationTimeMs INTEGER NULL,
    tokensUsed INTEGER NULL,
    modelUsed VARCHAR(100) NULL,

    -- Timestamps (using camelCase to match existing schema)
    createdAt TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ai_campaign_logs_campaign_id ON ai_campaign_logs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ai_campaign_logs_status ON ai_campaign_logs(status);
CREATE INDEX IF NOT EXISTS idx_ai_campaign_logs_created_at ON ai_campaign_logs(createdAt);
CREATE INDEX IF NOT EXISTS idx_ai_campaign_logs_model_used ON ai_campaign_logs(modelUsed);

-- Add comments to columns
COMMENT ON TABLE ai_campaign_logs IS 'Stores individual AI campaign generation requests and their results';
COMMENT ON COLUMN ai_campaign_logs.id IS 'Unique identifier for the AI campaign log entry';
COMMENT ON COLUMN ai_campaign_logs.campaign_id IS 'AI Campaign identifier from generation process';
COMMENT ON COLUMN ai_campaign_logs.status IS 'Generation status: success, error, partial, pending';
COMMENT ON COLUMN ai_campaign_logs.campaignDescription IS 'Original AI campaign description from user';
COMMENT ON COLUMN ai_campaign_logs.errorMessage IS 'Error message if generation failed';
COMMENT ON COLUMN ai_campaign_logs.generatedFlow IS 'Complete generated AI campaign flow JSON';
COMMENT ON COLUMN ai_campaign_logs.generationTimeMs IS 'Total generation time in milliseconds';
COMMENT ON COLUMN ai_campaign_logs.tokensUsed IS 'Total tokens used for LLM generation';
COMMENT ON COLUMN ai_campaign_logs.modelUsed IS 'LLM model used for generation';
COMMENT ON COLUMN ai_campaign_logs.createdAt IS 'Timestamp when AI campaign was created';
COMMENT ON COLUMN ai_campaign_logs.updatedAt IS 'Timestamp when record was last updated';

-- ============================================================================
-- AI CAMPAIGN METRICS TABLE
-- Stores aggregated daily AI campaign generation metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_campaign_metrics (
    -- Primary identifier
    id TEXT(255) NOT NULL PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Date for which metrics are collected
    date TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Performance averages (using camelCase to match existing schema)
    averageGenerationTimeMs DOUBLE PRECISION NULL,
    averageTokensUsed DOUBLE PRECISION NULL,

    -- Usage statistics broken down by model
    modelUsage JSONB NULL,

    -- Counters (using camelCase to match existing schema)
    successfulGenerations INTEGER NOT NULL DEFAULT 0,
    failedGenerations INTEGER NOT NULL DEFAULT 0,
    partialGenerations INTEGER NOT NULL DEFAULT 0,
    totalRequests INTEGER NOT NULL DEFAULT 0,

    -- Additional AI-specific metrics
    totalNodesGenerated INTEGER NULL DEFAULT 0,
    totalValidationIssues INTEGER NULL DEFAULT 0,
    averageQualityScore DOUBLE PRECISION NULL,

    -- Timestamps
    createdAt TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for metrics table
CREATE INDEX IF NOT EXISTS idx_ai_campaign_metrics_date ON ai_campaign_metrics(date);
CREATE INDEX IF NOT EXISTS idx_ai_campaign_metrics_created_at ON ai_campaign_metrics(createdAt);

-- Add comments to metrics columns
COMMENT ON TABLE ai_campaign_metrics IS 'Stores aggregated daily AI campaign generation metrics';
COMMENT ON COLUMN ai_campaign_metrics.id IS 'Unique identifier for the AI metrics record';
COMMENT ON COLUMN ai_campaign_metrics.date IS 'Date for which metrics are collected';
COMMENT ON COLUMN ai_campaign_metrics.averageGenerationTimeMs IS 'Average generation time in milliseconds';
COMMENT ON COLUMN ai_campaign_metrics.averageTokensUsed IS 'Average tokens used per generation';
COMMENT ON COLUMN ai_campaign_metrics.modelUsage IS 'Usage statistics broken down by model';
COMMENT ON COLUMN ai_campaign_metrics.successfulGenerations IS 'Number of successful AI campaign generations';
COMMENT ON COLUMN ai_campaign_metrics.failedGenerations IS 'Number of failed AI campaign generations';
COMMENT ON COLUMN ai_campaign_metrics.partialGenerations IS 'Number of partial AI campaign generations';
COMMENT ON COLUMN ai_campaign_metrics.totalRequests IS 'Total number of AI campaign generation requests';
COMMENT ON COLUMN ai_campaign_metrics.totalNodesGenerated IS 'Total number of campaign nodes generated';
COMMENT ON COLUMN ai_campaign_metrics.totalValidationIssues IS 'Total validation issues found';
COMMENT ON COLUMN ai_campaign_metrics.averageQualityScore IS 'Average quality score of generated campaigns';
COMMENT ON COLUMN ai_campaign_metrics.createdAt IS 'Timestamp when metrics record was created';
COMMENT ON COLUMN ai_campaign_metrics.updatedAt IS 'Timestamp when record was last updated';

-- ============================================================================
-- AI USER FEEDBACK TABLE
-- Stores user feedback on AI generated campaigns
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_user_feedback (
    -- Primary identifier
    id TEXT(255) NOT NULL PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Feedback details
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedbackText TEXT NULL,

    -- Reference to AI campaign log (using camelCase to match existing schema)
    campaignLogId TEXT NOT NULL,

    -- Structured issues data
    issues JSONB NULL,

    -- Additional feedback fields
    userId VARCHAR(255) NULL,
    wouldUseAgain BOOLEAN NULL,
    difficultyRating INTEGER NULL CHECK (difficultyRating >= 1 AND rating <= 5),

    -- Timestamp
    createdAt TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for feedback table
CREATE INDEX IF NOT EXISTS idx_ai_user_feedback_campaign_log_id ON ai_user_feedback(campaignLogId);
CREATE INDEX IF NOT EXISTS idx_ai_user_feedback_rating ON ai_user_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_ai_user_feedback_created_at ON ai_user_feedback(createdAt);
CREATE INDEX IF NOT EXISTS idx_ai_user_feedback_user_id ON ai_user_feedback(userId);

-- Add comments to feedback columns
COMMENT ON TABLE ai_user_feedback IS 'Stores user feedback on AI generated campaigns';
COMMENT ON COLUMN ai_user_feedback.id IS 'Unique identifier for the feedback record';
COMMENT ON COLUMN ai_user_feedback.rating IS 'Rating from 1-5 provided by user';
COMMENT ON COLUMN ai_user_feedback.feedbackText IS 'Text feedback provided by user';
COMMENT ON COLUMN ai_user_feedback.campaignLogId IS 'Reference to the AI campaign log this feedback is for';
COMMENT ON COLUMN ai_user_feedback.issues IS 'Specific issues reported in structured format';
COMMENT ON COLUMN ai_user_feedback.userId IS 'User identifier who provided feedback';
COMMENT ON COLUMN ai_user_feedback.wouldUseAgain IS 'Whether user would use AI campaign generation again';
COMMENT ON COLUMN ai_user_feedback.difficultyRating IS 'Difficulty rating from 1-5 for using the campaign';
COMMENT ON COLUMN ai_user_feedback.createdAt IS 'Timestamp when feedback was provided';

-- ============================================================================
-- AI SYSTEM METRICS TABLE
-- Stores AI system performance and health metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_system_metrics (
    -- Primary identifier (using UUID type)
    id UUID NOT NULL PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Timestamp (with timezone for system metrics)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- AI system performance metrics
    active_requests INTEGER NOT NULL DEFAULT 0,
    queue_length INTEGER NOT NULL DEFAULT 0,
    average_response_time_ms DOUBLE PRECISION NULL,
    error_rate DOUBLE PRECISION NULL,
    memory_usage_mb DOUBLE PRECISION NULL,
    cpu_usage_percent DOUBLE PRECISION NULL,

    -- AI LLM API metrics
    llm_api_calls INTEGER NOT NULL DEFAULT 0,
    llm_api_errors INTEGER NOT NULL DEFAULT 0,
    cache_hit_rate DOUBLE PRECISION NULL,
    model_switches INTEGER NULL DEFAULT 0,

    -- AI-specific metrics
    ai_model_in_use VARCHAR(100) NULL,
    average_generation_complexity VARCHAR(20) NULL,
    validation_success_rate DOUBLE PRECISION NULL,
    auto_correction_rate DOUBLE PRECISION NULL,

    -- Timestamp (with timezone)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create indexes for system metrics
CREATE INDEX IF NOT EXISTS idx_ai_system_metrics_timestamp ON ai_system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_system_metrics_created_at ON ai_system_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_system_metrics_model_in_use ON ai_system_metrics(ai_model_in_use);

-- Add comments to system metrics columns
COMMENT ON TABLE ai_system_metrics IS 'Stores AI system performance and health metrics';
COMMENT ON COLUMN ai_system_metrics.id IS 'Unique identifier for the AI system metrics record';
COMMENT ON COLUMN ai_system_metrics.timestamp IS 'Timestamp when metrics were collected';
COMMENT ON COLUMN ai_system_metrics.active_requests IS 'Number of active AI campaign generation requests';
COMMENT ON COLUMN ai_system_metrics.queue_length IS 'Number of requests in queue';
COMMENT ON COLUMN ai_system_metrics.average_response_time_ms IS 'Average response time for the period';
COMMENT ON COLUMN ai_system_metrics.error_rate IS 'Error rate as percentage (0-100)';
COMMENT ON COLUMN ai_system_metrics.memory_usage_mb IS 'Memory usage in MB';
COMMENT ON COLUMN ai_system_metrics.cpu_usage_percent IS 'CPU usage as percentage';
COMMENT ON COLUMN ai_system_metrics.llm_api_calls IS 'Number of LLM API calls made';
COMMENT ON COLUMN ai_system_metrics.llm_api_errors IS 'Number of LLM API errors';
COMMENT ON COLUMN ai_system_metrics.cache_hit_rate IS 'Cache hit rate as percentage (0-100)';
COMMENT ON COLUMN ai_system_metrics.model_switches IS 'Number of AI model switches';
COMMENT ON COLUMN ai_system_metrics.ai_model_in_use IS 'Currently active AI model';
COMMENT ON COLUMN ai_system_metrics.average_generation_complexity IS 'Average complexity of generated campaigns';
COMMENT ON COLUMN ai_system_metrics.validation_success_rate IS 'Success rate of campaign validation';
COMMENT ON COLUMN ai_system_metrics.auto_correction_rate IS 'Rate of auto-corrections applied';
COMMENT ON COLUMN ai_system_metrics.created_at IS 'Timestamp when record was created';

-- ============================================================================
-- TRIGGERS AND FUNCTIONS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Function to automatically update updatedAt timestamp
CREATE OR REPLACE FUNCTION update_ai_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updatedAt = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updatedAt columns
CREATE TRIGGER update_ai_campaign_logs_updated_at
    BEFORE UPDATE ON ai_campaign_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_updated_at_column();

CREATE TRIGGER update_ai_campaign_metrics_updated_at
    BEFORE UPDATE ON ai_campaign_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_updated_at_column();

-- ============================================================================
-- VALIDATION CONSTRAINTS
-- ============================================================================

-- Add check constraints for data integrity
ALTER TABLE ai_campaign_logs
ADD CONSTRAINT IF NOT EXISTS chk_ai_campaign_logs_status
CHECK (status IN ('success', 'error', 'partial', 'pending'));

ALTER TABLE ai_user_feedback
ADD CONSTRAINT IF NOT EXISTS chk_ai_user_feedback_rating
CHECK (rating >= 1 AND rating <= 5);

ALTER TABLE ai_user_feedback
ADD CONSTRAINT IF NOT EXISTS chk_ai_user_feedback_difficulty_rating
CHECK (difficultyRating >= 1 AND difficultyRating <= 5);

ALTER TABLE ai_system_metrics
ADD CONSTRAINT IF NOT EXISTS chk_ai_system_metrics_error_rate
CHECK (error_rate >= 0 AND error_rate <= 100);

ALTER TABLE ai_system_metrics
ADD CONSTRAINT IF NOT EXISTS chk_ai_system_metrics_cpu_usage
CHECK (cpu_usage_percent >= 0 AND cpu_usage_percent <= 100);

ALTER TABLE ai_system_metrics
ADD CONSTRAINT IF NOT EXISTS chk_ai_system_metrics_cache_hit_rate
CHECK (cache_hit_rate >= 0 AND cache_hit_rate <= 100);

ALTER TABLE ai_campaign_metrics
ADD CONSTRAINT IF NOT EXISTS chk_ai_campaign_metrics_quality_score
CHECK (averageQualityScore >= 0 AND averageQualityScore <= 100);

ALTER TABLE ai_campaign_metrics
ADD CONSTRAINT IF NOT EXISTS chk_ai_campaign_metrics_validation_rate
CHECK (validation_success_rate >= 0 AND validation_success_rate <= 100);

ALTER TABLE ai_campaign_metrics
ADD CONSTRAINT IF NOT EXISTS chk_ai_campaign_metrics_correction_rate
CHECK (auto_correction_rate >= 0 AND auto_correction_rate <= 100);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for AI campaign performance summary
CREATE OR REPLACE VIEW ai_campaign_performance_summary AS
SELECT
    DATE_TRUNC('day', cl.createdAt) as date,
    COUNT(*) as total_campaigns,
    COUNT(CASE WHEN cl.status = 'success' THEN 1 END) as successful_campaigns,
    COUNT(CASE WHEN cl.status = 'error' THEN 1 END) as failed_campaigns,
    COUNT(CASE WHEN cl.status = 'partial' THEN 1 END) as partial_campaigns,
    AVG(cl.generationTimeMs) as avg_generation_time_ms,
    AVG(cl.tokensUsed) as avg_tokens_used,
    cl.modelUsed,
    -- Extract node count from generatedFlow JSON
    (jsonb_array_length(cl.generatedFlow->'steps')::INTEGER) as avg_nodes_per_campaign
FROM ai_campaign_logs cl
GROUP BY DATE_TRUNC('day', cl.createdAt), cl.modelUsed
ORDER BY date DESC;

-- View for recent AI campaigns with feedback
CREATE OR REPLACE VIEW ai_recent_campaigns_with_feedback AS
SELECT
    cl.id,
    cl.campaign_id,
    cl.status,
    cl.campaignDescription,
    cl.generationTimeMs,
    cl.modelUsed,
    cl.createdAt,
    -- Extract key metrics from generatedFlow
    jsonb_array_length(cl.generatedFlow->'steps') as node_count,
    cl.generatedFlow->'validation'->'total_issues' as validation_issues,
    cl.generatedFlow->'validation'->'corrections_applied' as corrections_applied,
    -- Feedback information
    uf.rating as user_rating,
    uf.feedbackText as user_feedback,
    uf.wouldUseAgain,
    uf.difficultyRating as user_difficulty_rating,
    uf.createdAt as feedback_date
FROM ai_campaign_logs cl
LEFT JOIN ai_user_feedback uf ON cl.id = uf.campaignLogId
ORDER BY cl.createdAt DESC
LIMIT 100;

-- View for AI system health dashboard
CREATE OR REPLACE VIEW ai_system_health_dashboard AS
SELECT
    DATE_TRUNC('hour', sm.timestamp) as hour,
    AVG(sm.active_requests) as avg_active_requests,
    AVG(sm.queue_length) as avg_queue_length,
    AVG(sm.average_response_time_ms) as avg_response_time_ms,
    AVG(sm.error_rate) as avg_error_rate,
    AVG(sm.llm_api_calls) as total_llm_calls,
    AVG(sm.cache_hit_rate) as avg_cache_hit_rate,
    sm.ai_model_in_use,
    AVG(sm.validation_success_rate) as avg_validation_success_rate,
    AVG(sm.auto_correction_rate) as avg_auto_correction_rate
FROM ai_system_metrics sm
WHERE sm.timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', sm.timestamp), sm.ai_model_in_use
ORDER BY hour DESC;

-- View for AI model performance comparison
CREATE OR REPLACE VIEW ai_model_performance_comparison AS
SELECT
    cl.modelUsed,
    COUNT(*) as total_campaigns,
    COUNT(CASE WHEN cl.status = 'success' THEN 1 END) as successful_campaigns,
    AVG(cl.generationTimeMs) as avg_generation_time_ms,
    AVG(cl.tokensUsed) as avg_tokens_used,
    AVG(jsonb_array_length(cl.generatedFlow->'steps')::INTEGER) as avg_nodes_generated,
    AVG(CAST(cl.generatedFlow->'validation'->'total_issues' AS INTEGER)) as avg_validation_issues,
    DATE_TRUNC('day', cl.createdAt) as date
FROM ai_campaign_logs cl
WHERE cl.createdAt >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY cl.modelUsed, DATE_TRUNC('day', cl.createdAt)
ORDER BY date DESC, successful_campaigns DESC;

-- ============================================================================
-- MIGRATION TRACKING
-- ============================================================================

-- Create migration tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS ai_migration_history (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    tables_created TEXT[],
    CONSTRAINT ai_migration_history_version_unique UNIQUE (version)
);

-- Record this migration
INSERT INTO ai_migration_history (version, description, execution_time_ms, tables_created)
VALUES (
    '2.0',
    'AI Campaign Generation System Schema Initialization with ai_ prefixed tables',
    0,
    ARRAY['ai_campaign_logs', 'ai_campaign_metrics', 'ai_user_feedback', 'ai_system_metrics']
) ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS (Optional - uncomment for strict referential integrity)
-- ============================================================================

-- Uncomment these if you want strict foreign key constraints
-- ALTER TABLE ai_user_feedback
-- ADD CONSTRAINT fk_ai_user_feedback_campaign_log_id
-- FOREIGN KEY (campaignLogId) REFERENCES ai_campaign_logs(id)
-- ON DELETE CASCADE;

-- ============================================================================
-- SAMPLE DATA INSERTIONS (Optional - for testing)
-- ============================================================================

-- Sample AI campaign log (commented out - uncomment for testing)
-- INSERT INTO ai_campaign_logs (
--     campaign_id, status, campaignDescription, generatedFlow,
--     generationTimeMs, modelUsed, tokensUsed
-- ) VALUES (
--     'ai_campaign_sample_001',
--     'success',
--     'AI generated welcome campaign for new subscribers',
--     '{"initialStepID": "welcome-ai-001", "steps": [{"id": "welcome-ai-001", "type": "message", "content": "Welcome!"}]}',
--     5000,
--     'openai/gpt-4o-mini',
--     1200
-- );

-- Sample AI campaign metrics (commented out - uncomment for testing)
-- INSERT INTO ai_campaign_metrics (
--     successfulGenerations, failedGenerations, totalRequests,
--     averageGenerationTimeMs, averageTokensUsed, totalNodesGenerated,
--     averageQualityScore
-- ) VALUES (
--     10, 2, 12, 4500.5, 1100.3, 85, 92.5
-- );

-- ============================================================================
-- COMPLETION
-- ============================================================================

COMMIT;

-- AI Campaign Migration completed successfully!
-- All AI campaign tables, indexes, views, and constraints have been created.