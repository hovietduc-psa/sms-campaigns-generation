"""
Database models for SMS Campaign Generation System.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Float, DateTime, Date, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.core.database import Base


class CampaignLog(Base):
    """Model for storing campaign generation logs."""

    __tablename__ = "campaign_logs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for the campaign log"
    )

    campaign_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Campaign identifier from generation process"
    )

    request_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique request identifier"
    )

    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="User identifier who requested the campaign"
    )

    campaign_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original campaign description from user"
    )

    generated_flow: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Complete generated campaign flow JSON"
    )

    generation_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total generation time in milliseconds"
    )

    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total tokens used for LLM generation"
    )

    model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="LLM model used for generation"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Generation status: success, error, partial"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if generation failed"
    )

    node_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of nodes in generated campaign"
    )

    validation_issues: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        comment="Number of validation issues found"
    )

    corrections_applied: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        comment="Number of auto-corrections applied"
    )

    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Campaign quality score (0-100)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when campaign was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated"
    )


class CampaignMetrics(Base):
    """Model for storing daily campaign generation metrics."""

    __tablename__ = "campaign_metrics"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for the metrics record"
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        unique=True,
        index=True,
        comment="Date for which metrics are collected"
    )

    total_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of campaign generation requests"
    )

    successful_generations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of successful campaign generations"
    )

    failed_generations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of failed campaign generations"
    )

    partial_generations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of partial campaign generations"
    )

    average_generation_time_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Average generation time in milliseconds"
    )

    average_tokens_used: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Average tokens used per generation"
    )

    average_quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Average quality score across all campaigns"
    )

    model_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Usage statistics broken down by model"
    )

    total_nodes_generated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of campaign nodes generated"
    )

    total_validation_issues: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of validation issues across all campaigns"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when metrics record was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated"
    )


class UserFeedback(Base):
    """Model for storing user feedback on generated campaigns."""

    __tablename__ = "user_feedback"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for the feedback record"
    )

    campaign_log_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the campaign log this feedback is for"
    )

    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="User who provided the feedback"
    )

    rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Rating from 1-5 provided by user"
    )

    feedback_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Text feedback provided by user"
    )

    issues: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Specific issues reported in structured format"
    )

    would_use_again: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether user would use this campaign again"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when feedback was provided"
    )


class SystemMetrics(Base):
    """Model for storing system performance and health metrics."""

    __tablename__ = "system_metrics"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for the system metrics record"
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp when metrics were collected"
    )

    active_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of active campaign generation requests"
    )

    queue_length: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of requests in queue"
    )

    average_response_time_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Average response time for the period"
    )

    error_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Error rate as percentage (0-100)"
    )

    memory_usage_mb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Memory usage in MB"
    )

    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="CPU usage as percentage"
    )

    llm_api_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of LLM API calls made"
    )

    llm_api_errors: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of LLM API errors"
    )

    cache_hit_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Cache hit rate as percentage (0-100)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created"
    )