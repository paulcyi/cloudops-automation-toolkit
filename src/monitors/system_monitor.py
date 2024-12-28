from typing import Dict
from prometheus_client import Gauge, start_http_server

class SystemMonitor:
    """
    SystemMonitor class for collecting and reporting system metrics.
    """
    def __init__(self, metrics_port: int = 8000):
        """
        Initialize the SystemMonitor with Prometheus metrics.
        
        Args:
            metrics_port: Port number for Prometheus metrics server
        """
        # Initialize Prometheus metrics
        self.cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage in percent')
        self.memory_usage = Gauge('system_memory_usage_percent', 'Memory usage in percent')
        self.disk_usage = Gauge('system_disk_usage_percent', 'Disk usage in percent')
        
        # Start Prometheus metrics server
        start_http_server(metrics_port)