import pytest
from prometheus_client import CollectorRegistry
from src.monitors.system_monitor import SystemMonitor

@pytest.fixture
def system_monitor():
    """
    Fixture to create a fresh SystemMonitor instance for each test.
    Returns a configured SystemMonitor instance with a clean registry.
    """
    registry = CollectorRegistry()
    monitor = SystemMonitor(registry=registry)
    return monitor

def test_system_monitor_initialization(system_monitor):
    """
    Test that SystemMonitor initializes correctly with proper Prometheus metrics.
    """
    # Verify that the monitor instance is created successfully
    assert system_monitor is not None
    
    # Verify that the registry contains the expected metrics
    metrics = [metric.name for metric in system_monitor.registry.collect()]
    expected_metrics = [
        'system_cpu_usage',
        'system_memory_usage',
        'system_disk_usage'
    ]
    for metric in expected_metrics:
        assert metric in metrics

def test_cpu_metrics_collection(system_monitor):
    """
    Test CPU metrics collection functionality.
    """
    # Collect CPU metrics
    metrics = system_monitor.collect_cpu_metrics()
    
    # Verify the structure and basic validity of collected metrics
    assert isinstance(metrics, dict)
    assert 'usage_percent' in metrics
    assert 0 <= metrics['usage_percent'] <= 100

def test_memory_metrics_collection(system_monitor):
    """
    Test memory metrics collection functionality.
    """
    # Collect memory metrics
    metrics = system_monitor.collect_memory_metrics()
    
    # Verify the structure and basic validity of collected metrics
    assert isinstance(metrics, dict)
    assert all(key in metrics for key in ['total', 'used', 'free'])
    assert metrics['total'] > 0
    assert metrics['used'] >= 0
    assert metrics['free'] >= 0
    assert metrics['total'] >= metrics['used']

def test_disk_metrics_collection(system_monitor):
    """
    Test disk metrics collection functionality.
    """
    # Collect disk metrics
    metrics = system_monitor.collect_disk_metrics()
    
    # Verify the structure and basic validity of collected metrics
    assert isinstance(metrics, dict)
    assert all(key in metrics for key in ['total', 'used', 'free'])
    assert metrics['total'] > 0
    assert metrics['used'] >= 0
    assert metrics['free'] >= 0
    assert metrics['total'] >= metrics['used']

def test_metrics_update(system_monitor):
    """
    Test that metrics are properly updated in the Prometheus registry.
    """
    # Update all metrics
    system_monitor.update_metrics()
    
    # Collect all metrics from the registry
    collected_metrics = {
        metric.name: metric
        for metric in system_monitor.registry.collect()
    }
    
    # Verify that all expected metrics are present and have values
    expected_metrics = [
        'system_cpu_usage',
        'system_memory_usage',
        'system_disk_usage'
    ]
    
    for metric_name in expected_metrics:
        assert metric_name in collected_metrics
        metric = collected_metrics[metric_name]
        assert len(metric.samples) > 0
        for sample in metric.samples:
            assert isinstance(sample.value, (int, float))

@pytest.mark.integration
def test_continuous_monitoring(system_monitor):
    """
    Integration test for continuous monitoring functionality.
    """
    import time
    
    # Collect metrics multiple times
    readings = []
    for _ in range(3):
        system_monitor.update_metrics()
        metrics = {
            metric.name: metric
            for metric in system_monitor.registry.collect()
        }
        readings.append(metrics)
        time.sleep(1)
    
    # Verify that we get different readings
    cpu_values = [
        reading['system_cpu_usage'].samples[0].value
        for reading in readings
    ]
    assert len(set(cpu_values)) > 1, "CPU usage values should vary over time"