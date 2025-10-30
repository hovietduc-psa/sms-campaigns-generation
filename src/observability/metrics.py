"""
Metrics collection and monitoring.
"""
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Simple metric data structure."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = None


class MetricsService:
    """Simple metrics service for tracking API performance."""

    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, list] = {}

    def increment(self, metric_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        key = self._make_key(metric_name, tags)
        self.counters[key] = self.counters.get(key, 0) + value

    def gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric."""
        key = self._make_key(metric_name, tags)
        self.metrics[key] = Metric(
            name=metric_name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )

    def timer(self, metric_name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timer metric."""
        key = self._make_key(metric_name, tags)
        if key not in self.timers:
            self.timers[key] = []
        self.timers[key].append(duration_ms)

        # Keep only last 100 measurements
        if len(self.timers[key]) > 100:
            self.timers[key] = self.timers[key][-100:]

    def get_stats(self, metric_name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """Get statistics for a timer metric."""
        key = self._make_key(metric_name, tags)
        if key not in self.timers or not self.timers[key]:
            return {}

        values = self.timers[key]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": sorted(values)[len(values) // 2],
            "p95": sorted(values)[int(len(values) * 0.95)],
            "p99": sorted(values)[int(len(values) * 0.99)],
        }

    def _make_key(self, metric_name: str, tags: Dict[str, str] = None) -> str:
        """Create a unique key for a metric with tags."""
        if not tags:
            return metric_name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"

    def log_metric(self, metric_name: str, value: float, metric_type: str = "counter", tags: Dict[str, str] = None):
        """Log a metric (simple console output)."""
        tag_str = ""
        if tags:
            tag_str = " " + " ".join(f"{k}={v}" for k, v in tags.items())

        logger.info(f"METRIC: {metric_name}={value} ({metric_type}){tag_str}")


# Global metrics instance
_metrics_service = None


def get_metrics_service() -> MetricsService:
    """Get the global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def increment_metric(name: str, value: int = 1, tags: Dict[str, str] = None):
    """Convenience function to increment a metric."""
    get_metrics_service().increment(name, value, tags)


def gauge_metric(name: str, value: float, tags: Dict[str, str] = None):
    """Convenience function to set a gauge metric."""
    get_metrics_service().gauge(name, value, tags)


def timer_metric(name: str, duration_ms: float, tags: Dict[str, str] = None):
    """Convenience function to record a timer metric."""
    get_metrics_service().timer(name, duration_ms, tags)