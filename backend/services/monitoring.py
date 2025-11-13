#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitoring Service - Prometheus Metrics and Health Checks

Provides:
- Prometheus metrics for all agents
- Health check endpoints
- Performance monitoring
- Error rate tracking
- Business KPI metrics

Metrics include:
- Agent execution times
- Task success/failure rates
- API call counts
- Cache hit rates
- Business metrics (revenue, ROI, etc.)
"""

from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"       # Always increasing
    GAUGE = "gauge"           # Can go up or down  
    HISTOGRAM = "histogram"   # Distribution
    SUMMARY = "summary"       # Distribution with quantiles


class Metric:
    """Individual metric."""
    
    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 0
    ):
        """
        Initialize metric.
        
        Args:
            name: Metric name
            metric_type: Type of metric
            description: Human-readable description
            labels: Optional labels/tags
            value: Initial value
        """
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.labels = labels or {}
        self.value = value
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
    
    def increment(self, amount: float = 1) -> None:
        """Increment metric value."""
        self.value += amount
        self.last_updated = datetime.now()
    
    def set(self, value: float) -> None:
        """Set metric value."""
        self.value = value
        self.last_updated = datetime.now()
    
    def observe(self, value: float) -> None:
        """Record observation (for histograms/summaries)."""
        # For histograms/summaries, store observations
        if not hasattr(self, 'observations'):
            self.observations = []
        self.observations.append(value)
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "value": self.value,
            "labels": self.labels,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }


class MetricsCollector:
    """
    Collects Prometheus-style metrics.
    
    Tracks:
    - Agent performance (execution time, success rate)
    - API calls (count, latency)
    - Database operations
    - Cache performance
    - Business metrics
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Metric] = {}
        self._initialize_metrics()
        logger.info("Metrics collector initialized")
    
    def _initialize_metrics(self) -> None:
        """Initialize all default metrics."""
        
        # Agent metrics
        self.register_metric(
            "agent_execution_time_seconds",
            MetricType.HISTOGRAM,
            "Agent execution time in seconds"
        )
        self.register_metric(
            "agent_tasks_completed_total",
            MetricType.COUNTER,
            "Total tasks completed by agents"
        )
        self.register_metric(
            "agent_tasks_failed_total",
            MetricType.COUNTER,
            "Total tasks failed by agents"
        )
        self.register_metric(
            "agent_tasks_running",
            MetricType.GAUGE,
            "Currently running agent tasks"
        )
        
        # API metrics
        self.register_metric(
            "api_requests_total",
            MetricType.COUNTER,
            "Total API requests"
        )
        self.register_metric(
            "api_request_latency_seconds",
            MetricType.HISTOGRAM,
            "API request latency"
        )
        self.register_metric(
            "api_errors_total",
            MetricType.COUNTER,
            "Total API errors"
        )
        
        # Database metrics
        self.register_metric(
            "db_queries_total",
            MetricType.COUNTER,
            "Total database queries"
        )
        self.register_metric(
            "db_query_latency_seconds",
            MetricType.HISTOGRAM,
            "Database query latency"
        )
        
        # Cache metrics
        self.register_metric(
            "cache_hits_total",
            MetricType.COUNTER,
            "Cache hits"
        )
        self.register_metric(
            "cache_misses_total",
            MetricType.COUNTER,
            "Cache misses"
        )
        
        # Business metrics
        self.register_metric(
            "business_revenue_dollars",
            MetricType.GAUGE,
            "Monthly revenue in dollars"
        )
        self.register_metric(
            "business_roi_percent",
            MetricType.GAUGE,
            "Return on investment percentage"
        )
        self.register_metric(
            "business_active_products",
            MetricType.GAUGE,
            "Number of active products"
        )
        self.register_metric(
            "business_profit_dollars",
            MetricType.GAUGE,
            "Monthly profit in dollars"
        )
    
    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        initial_value: float = 0
    ) -> Metric:
        """Register a new metric."""
        metric = Metric(name, metric_type, description, value=initial_value)
        self.metrics[name] = metric
        logger.debug(f"Registered metric: {name}")
        return metric
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name."""
        return self.metrics.get(name)
    
    def increment_counter(self, name: str, amount: float = 1) -> None:
        """Increment a counter metric."""
        metric = self.get_metric(name)
        if metric and metric.metric_type == MetricType.COUNTER:
            metric.increment(amount)
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric value."""
        metric = self.get_metric(name)
        if metric and metric.metric_type == MetricType.GAUGE:
            metric.set(value)
    
    def observe_histogram(self, name: str, value: float) -> None:
        """Observe a value in histogram metric."""
        metric = self.get_metric(name)
        if metric and metric.metric_type == MetricType.HISTOGRAM:
            metric.observe(value)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics as dictionaries."""
        return {name: metric.to_dict() for name, metric in self.metrics.items()}
    
    def get_prometheus_format(self) -> str:
        """Generate Prometheus text format output."""
        lines = []
        
        for name, metric in self.metrics.items():
            # Add HELP line
            lines.append(f"# HELP {name} {metric.description}")
            # Add TYPE line
            lines.append(f"# TYPE {name} {metric.metric_type.value}")
            # Add metric value line
            label_str = ""
            if metric.labels:
                labels = ','.join(f'{k}="{v}"' for k, v in metric.labels.items())
                label_str = f"{{{labels}}}"
            lines.append(f"{name}{label_str} {metric.value}")
            lines.append("")
        
        return "\n".join(lines)


class HealthCheck:
    """Health check status."""
    
    def __init__(self):
        """Initialize health check."""
        self.services: Dict[str, Dict[str, Any]] = {}
        self.last_check = datetime.now()
    
    def set_service_status(
        self,
        service_name: str,
        is_healthy: bool,
        message: str = "",
        response_time_ms: float = 0
    ) -> None:
        """Set service health status."""
        self.services[service_name] = {
            "healthy": is_healthy,
            "message": message,
            "response_time_ms": response_time_ms,
            "last_checked": datetime.now().isoformat()
        }
    
    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        return all(s.get("healthy", False) for s in self.services.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_status": "healthy" if self.is_healthy() else "unhealthy",
            "services": self.services,
            "last_check": self.last_check.isoformat(),
            "timestamp": datetime.now().isoformat()
        }


# Global instances
_metrics_collector: Optional[MetricsCollector] = None
_health_check: Optional[HealthCheck] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector (singleton)."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_health_check() -> HealthCheck:
    """Get global health check (singleton)."""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check


class MetricsContext:
    """Context manager for tracking operation metrics."""
    
    def __init__(self, metric_name: str, operation_name: str):
        """Initialize context."""
        self.metric_name = metric_name
        self.operation_name = operation_name
        self.start_time = None
        self.collector = get_metrics_collector()
    
    def __enter__(self):
        """Enter context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        elapsed = time.time() - self.start_time
        
        # Record execution time
        self.collector.observe_histogram(f"{self.metric_name}_latency_seconds", elapsed)
        
        if exc_type is None:
            # Success
            self.collector.increment_counter(f"{self.metric_name}_success_total")
        else:
            # Failure
            self.collector.increment_counter(f"{self.metric_name}_error_total")
            logger.error(f"{self.operation_name} failed: {exc_val}")
        
        return False  # Don't suppress exceptions


# Convenience functions
def record_agent_execution(agent_name: str, elapsed_seconds: float, success: bool) -> None:
    """Record agent execution metrics."""
    collector = get_metrics_collector()
    collector.observe_histogram("agent_execution_time_seconds", elapsed_seconds)
    
    if success:
        collector.increment_counter("agent_tasks_completed_total")
    else:
        collector.increment_counter("agent_tasks_failed_total")


def record_api_call(endpoint: str, latency_seconds: float, success: bool) -> None:
    """Record API call metrics."""
    collector = get_metrics_collector()
    collector.increment_counter("api_requests_total")
    collector.observe_histogram("api_request_latency_seconds", latency_seconds)
    
    if not success:
        collector.increment_counter("api_errors_total")


def update_business_metrics(
    revenue: float,
    profit: float,
    roi: float,
    active_products: int
) -> None:
    """Update business metrics."""
    collector = get_metrics_collector()
    collector.set_gauge("business_revenue_dollars", revenue)
    collector.set_gauge("business_profit_dollars", profit)
    collector.set_gauge("business_roi_percent", roi)
    collector.set_gauge("business_active_products", active_products)

