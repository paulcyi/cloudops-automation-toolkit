"""
System monitoring module providing resource metrics collection and Prometheus integration.
Monitors CPU, memory, and disk usage with configurable Prometheus metrics.
"""

from typing import Dict, Any
import psutil
from prometheus_client import Gauge, CollectorRegistry


class SystemMonitor:
    """
    A class to monitor system resources with Prometheus metrics integration.
    """

    def __init__(self, registry: CollectorRegistry = None):
        """
        Initialize the SystemMonitor with Prometheus metrics.

        Args:
            registry: A Prometheus CollectorRegistry instance for metrics collection
        """
        self.registry = registry or CollectorRegistry()

        # Initialize Prometheus metrics
        self.cpu_gauge = Gauge(
            "system_cpu_usage",
            "Current CPU usage in percentage",
            registry=self.registry,
        )

        self.memory_gauge = Gauge(
            "system_memory_usage",
            "Current memory usage in percentage",
            registry=self.registry,
        )

        self.disk_gauge = Gauge(
            "system_disk_usage",
            "Current disk usage in percentage",
            registry=self.registry,
        )

    def collect_cpu_metrics(self) -> Dict[str, float]:
        """
        Collect CPU metrics.

        Returns:
            Dict containing CPU usage statistics
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics = {
            "usage_percent": cpu_percent,
            "per_cpu_percent": psutil.cpu_percent(interval=None, percpu=True),
            "load_avg": psutil.getloadavg(),
        }
        self.cpu_gauge.set(cpu_percent)
        return metrics

    def collect_memory_metrics(self) -> Dict[str, Any]:
        """
        Collect memory metrics.

        Returns:
            Dict containing memory usage statistics
        """
        mem = psutil.virtual_memory()
        metrics = {
            "total": mem.total,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
        }
        self.memory_gauge.set(mem.percent)
        return metrics

    def collect_disk_metrics(self) -> Dict[str, Any]:
        """
        Collect disk metrics.

        Returns:
            Dict containing disk usage statistics
        """
        disk = psutil.disk_usage("/")
        metrics = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        }
        self.disk_gauge.set(disk.percent)
        return metrics

    def update_metrics(self) -> None:
        """Update all Prometheus metrics."""
        self.collect_cpu_metrics()
        self.collect_memory_metrics()
        self.collect_disk_metrics()
