-- Initialize database for SMS Campaign Generation System

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create campaign_logs table for storing generation logs
CREATE TABLE IF NOT EXISTS campaign_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_description TEXT NOT NULL,
    generated_flow JSONB NOT NULL,
    generation_time_ms INTEGER,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    status VARCHAR(50) NOT NULL, -- 'success', 'error', 'partial'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create campaign_metrics table for performance tracking
CREATE TABLE IF NOT EXISTS campaign_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    successful_generations INTEGER DEFAULT 0,
    failed_generations INTEGER DEFAULT 0,
    average_generation_time_ms FLOAT,
    average_tokens_used FLOAT,
    model_usage JSONB, -- Track usage by model
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);

-- Create user_feedback table for collecting feedback
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_log_id UUID REFERENCES campaign_logs(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    issues JSONB, -- Store specific issues reported
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_campaign_logs_created_at ON campaign_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_campaign_logs_status ON campaign_logs(status);
CREATE INDEX IF NOT EXISTS idx_campaign_logs_model_used ON campaign_logs(model_used);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_date ON campaign_metrics(date);
CREATE INDEX IF NOT EXISTS idx_user_feedback_campaign_log_id ON user_feedback(campaign_log_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_campaign_logs_updated_at
    BEFORE UPDATE ON campaign_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaign_metrics_updated_at
    BEFORE UPDATE ON campaign_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for daily statistics
CREATE OR REPLACE VIEW daily_campaign_stats AS
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE status = 'success') as successful_generations,
    COUNT(*) FILTER (WHERE status = 'error') as failed_generations,
    ROUND(AVG(generation_time_ms), 2) as average_generation_time_ms,
    ROUND(AVG(tokens_used), 2) as average_tokens_used,
    model_used
FROM campaign_logs
GROUP BY DATE(created_at), model_used
ORDER BY date DESC;