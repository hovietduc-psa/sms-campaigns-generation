"""
Fault-tolerant campaign logging service with async non-blocking operations.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from src.core.database import get_db_session
from src.core.config import get_settings
from src.models.database import CampaignLog, CampaignMetrics, UserFeedback, SystemMetrics

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseLogger:
    """
    Fault-tolerant database logging service.

    This service provides async logging capabilities that won't block the main application
    if the database is unavailable. It implements a write-through cache approach with
    graceful degradation.
    """

    def __init__(self):
        self._enabled = True
        self._connection_pool_size = 5
        self._retry_attempts = 3
        self._retry_delay = 1.0
        self._timeout = 5.0
        self._memory_fallback = []
        self._max_memory_fallback = 1000

    async def is_healthy(self) -> bool:
        """Check if database connection is healthy."""
        try:
            async for session in get_db_session():
                # Simple query to test connection
                await session.execute(select(func.now()))
                return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    async def log_campaign_generation(
        self,
        campaign_id: str,
        request_id: str,
        user_id: Optional[str],
        campaign_description: str,
        generated_flow: Dict[str, Any],
        generation_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        model_used: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        node_count: Optional[int] = None,
        validation_issues: int = 0,
        corrections_applied: int = 0,
        quality_score: Optional[float] = None,
    ) -> bool:
        """
        Log campaign generation to database asynchronously.

        Returns True if logging was successful, False otherwise.
        This method never raises exceptions to avoid blocking main operations.
        """
        if not self._enabled:
            return False

        try:
            # Create the log entry
            campaign_log = CampaignLog(
                campaign_id=campaign_id,
                request_id=request_id,
                user_id=user_id,
                campaign_description=campaign_description,
                generated_flow=generated_flow,
                generation_time_ms=generation_time_ms,
                tokens_used=tokens_used,
                model_used=model_used,
                status=status,
                error_message=error_message,
                node_count=node_count,
                validation_issues=validation_issues,
                corrections_applied=corrections_applied,
                quality_score=quality_score,
            )

            # Try to save to database
            success = await self._save_with_retry(campaign_log)

            if not success:
                # Fallback to memory cache if database fails
                await self._fallback_to_memory(campaign_log)

            # Always try to update metrics
            asyncio.create_task(
                self._update_daily_metrics_async(
                    status=status,
                    generation_time_ms=generation_time_ms,
                    tokens_used=tokens_used,
                    model_used=model_used,
                    node_count=node_count or 0,
                    validation_issues=validation_issues,
                    quality_score=quality_score,
                )
            )

            return success

        except Exception as e:
            logger.error(f"Unexpected error in log_campaign_generation: {e}", exc_info=True)
            return False

    async def _save_with_retry(self, campaign_log: CampaignLog) -> bool:
        """Save campaign log to database with retry logic."""
        for attempt in range(self._retry_attempts):
            try:
                async for session in get_db_session():
                    session.add(campaign_log)
                    await session.commit()
                    logger.info(f"Campaign log saved successfully: {campaign_log.request_id}")
                    return True
            except Exception as e:
                if attempt < self._retry_attempts - 1:
                    logger.warning(f"Database save attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(self._retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"All database save attempts failed for {campaign_log.request_id}: {e}")
                    return False
        return False

    async def _fallback_to_memory(self, campaign_log: CampaignLog) -> None:
        """Store campaign log in memory fallback cache."""
        try:
            # Add to memory cache (simple list for now)
            self._memory_fallback.append({
                'campaign_log': campaign_log,
                'timestamp': datetime.utcnow(),
                'retry_count': 0
            })

            # Limit memory fallback size
            if len(self._memory_fallback) > self._max_memory_fallback:
                self._memory_fallback.pop(0)  # Remove oldest

            logger.info(f"Campaign log stored in memory fallback: {campaign_log.request_id}")

            # Try to flush memory fallback periodically
            if len(self._memory_fallback) >= 10:  # Flush when we have 10+ items
                asyncio.create_task(self._flush_memory_fallback())

        except Exception as e:
            logger.error(f"Failed to store in memory fallback: {e}")

    async def _update_daily_metrics_async(
        self,
        status: str,
        generation_time_ms: Optional[int],
        tokens_used: Optional[int],
        model_used: Optional[str],
        node_count: int,
        validation_issues: int,
        quality_score: Optional[float],
    ) -> None:
        """Update daily metrics asynchronously (non-blocking)."""
        try:
            today = date.today()

            for attempt in range(2):  # Fewer retries for metrics
                try:
                    async for session in get_db_session():
                        # Get or create today's metrics
                        stmt = select(CampaignMetrics).where(CampaignMetrics.date == today)
                        result = await session.execute(stmt)
                        metrics = result.scalar_one_or_none()

                        if not metrics:
                            metrics = CampaignMetrics(date=today)
                            session.add(metrics)

                        # Update metrics
                        metrics.total_requests += 1

                        if status == "success":
                            metrics.successful_generations += 1
                        elif status == "error":
                            metrics.failed_generations += 1
                        else:
                            metrics.partial_generations += 1

                        # Update averages
                        if generation_time_ms:
                            if metrics.average_generation_time_ms:
                                metrics.average_generation_time_ms = (
                                    metrics.average_generation_time_ms + generation_time_ms
                                ) / 2
                            else:
                                metrics.average_generation_time_ms = generation_time_ms

                        if tokens_used:
                            if metrics.average_tokens_used:
                                metrics.average_tokens_used = (
                                    metrics.average_tokens_used + tokens_used
                                ) / 2
                            else:
                                metrics.average_tokens_used = tokens_used

                        if quality_score:
                            if metrics.average_quality_score:
                                metrics.average_quality_score = (
                                    metrics.average_quality_score + quality_score
                                ) / 2
                            else:
                                metrics.average_quality_score = quality_score

                        # Update model usage
                        if model_used:
                            if not metrics.model_usage:
                                metrics.model_usage = {}
                            model_usage = dict(metrics.model_usage)
                            model_usage[model_used] = model_usage.get(model_used, 0) + 1
                            metrics.model_usage = model_usage

                        # Update counts
                        if metrics.total_nodes_generated is None:
                            metrics.total_nodes_generated = 0
                        if metrics.total_validation_issues is None:
                            metrics.total_validation_issues = 0

                        metrics.total_nodes_generated += node_count
                        metrics.total_validation_issues += validation_issues

                        await session.commit()
                        logger.debug(f"Daily metrics updated for {today}")
                        return

                except Exception as e:
                    if attempt == 0:
                        logger.warning(f"Metrics update failed, retrying: {e}")
                        await asyncio.sleep(0.5)
                    else:
                        logger.error(f"Metrics update failed: {e}")
                        return

        except Exception as e:
            logger.error(f"Unexpected error in metrics update: {e}")

    async def _flush_memory_fallback(self) -> None:
        """Attempt to flush memory fallback to database."""
        if not self._memory_fallback:
            return

        items_to_flush = self._memory_fallback.copy()
        self._memory_fallback.clear()

        logger.info(f"Attempting to flush {len(items_to_flush)} items from memory fallback")

        for item in items_to_flush:
            campaign_log = item['campaign_log']
            retry_count = item['retry_count']

            if retry_count >= 3:  # Max retries
                logger.warning(f"Max retries exceeded for {campaign_log.request_id}, discarding")
                continue

            # Increment retry count
            item['retry_count'] = retry_count + 1

            success = await self._save_with_retry(campaign_log)
            if not success:
                # Put back in memory fallback with incremented retry count
                self._memory_fallback.append(item)

    async def log_user_feedback(
        self,
        campaign_log_id: UUID,
        user_id: Optional[str],
        rating: Optional[int] = None,
        feedback_text: Optional[str] = None,
        issues: Optional[Dict[str, Any]] = None,
        would_use_again: Optional[bool] = None,
    ) -> bool:
        """Log user feedback for a campaign."""
        try:
            feedback = UserFeedback(
                campaign_log_id=campaign_log_id,
                user_id=user_id,
                rating=rating,
                feedback_text=feedback_text,
                issues=issues,
                would_use_again=would_use_again,
            )

            async for session in get_db_session():
                session.add(feedback)
                await session.commit()
                logger.info(f"User feedback saved for campaign: {campaign_log_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to save user feedback: {e}")
            return False

    async def get_campaign_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        model_used: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[CampaignLog]:
        """Retrieve campaign logs with filtering options."""
        try:
            async for session in get_db_session():
                query = select(CampaignLog)

                # Apply filters
                if user_id:
                    query = query.where(CampaignLog.user_id == user_id)
                if status:
                    query = query.where(CampaignLog.status == status)
                if model_used:
                    query = query.where(CampaignLog.model_used == model_used)
                if date_from:
                    query = query.where(CampaignLog.created_at >= date_from)
                if date_to:
                    query = query.where(CampaignLog.created_at <= date_to)

                # Order and paginate
                query = query.order_by(CampaignLog.created_at.desc())
                query = query.offset(offset).limit(limit)

                result = await session.execute(query)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to retrieve campaign logs: {e}")
            return []

    async def get_daily_metrics(self, days: int = 30) -> List[CampaignMetrics]:
        """Retrieve daily metrics for the specified number of days."""
        try:
            async for session in get_db_session():
                query = select(CampaignMetrics).where(
                    CampaignMetrics.date >= date.today() - timedelta(days=days)
                ).order_by(CampaignMetrics.date.desc())

                result = await session.execute(query)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to retrieve daily metrics: {e}")
            return []

    def enable(self) -> None:
        """Enable database logging."""
        self._enabled = True
        logger.info("Database logging enabled")

    def disable(self) -> None:
        """Disable database logging."""
        self._enabled = False
        logger.info("Database logging disabled")

    def is_enabled(self) -> bool:
        """Check if database logging is enabled."""
        return self._enabled

    async def cleanup(self) -> None:
        """Cleanup resources and flush any remaining memory fallback."""
        if self._memory_fallback:
            await self._flush_memory_fallback()

        # Clear any remaining items
        self._memory_fallback.clear()
        logger.info("Database logger cleanup completed")


# Global instance
database_logger = DatabaseLogger()


def get_database_logger() -> DatabaseLogger:
    """Get the global database logger instance."""
    return database_logger