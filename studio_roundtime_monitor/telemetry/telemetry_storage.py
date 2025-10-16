"""
Telemetry storage backend for sending monitoring data to remote telemetry servers.

This module provides a unified interface for sending time interval data
to both Loki (for logs) and Prometheus (for metrics) based on data characteristics.
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .loki_client import LokiClient
from .prometheus_client import PrometheusClient

logger = logging.getLogger(__name__)


class TelemetryStorage:
    """
    Unified storage backend for sending monitoring data to telemetry infrastructure.
    
    This class determines whether to send data to Loki (for detailed logs) or
    Prometheus (for metrics) based on the data type and configuration.
    """
    
    def __init__(self, 
                 loki_url: Optional[str] = None,
                 prometheus_url: Optional[str] = None,
                 instance_id: str = "studio-roundtime-monitor",
                 job_name: str = "studio-roundtime-monitor"):
        """
        Initialize telemetry storage.
        
        Args:
            loki_url: URL of the Loki server (e.g., "http://100.64.0.113:3100")
            prometheus_url: URL of the Prometheus Pushgateway (e.g., "http://100.64.0.113:9091")
            instance_id: Instance identifier for this monitor
            job_name: Job name for Prometheus metrics
        """
        self.loki_client = None
        self.prometheus_client = None
        
        if loki_url:
            self.loki_client = LokiClient(loki_url, instance_id)
            logger.info(f"Initialized Loki client: {loki_url}")
        
        if prometheus_url:
            self.prometheus_client = PrometheusClient(prometheus_url, job_name)
            logger.info(f"Initialized Prometheus client: {prometheus_url}")
        
        if not self.loki_client and not self.prometheus_client:
            raise ValueError("At least one telemetry client (Loki or Prometheus) must be configured")
    
    def store_time_interval(self,
                          game_type: str,
                          table: str,
                          round_id: str,
                          interval_type: str,
                          duration: float,
                          additional_labels: Optional[Dict[str, str]] = None,
                          send_to_loki: bool = True,
                          send_to_prometheus: bool = True) -> Dict[str, bool]:
        """
        Store time interval data to telemetry servers.
        
        Args:
            game_type: Type of game (roulette, sicbo, tableapi)
            table: Table identifier
            round_id: Round identifier
            interval_type: Type of interval (e.g., "start-to-betstop")
            duration: Duration in seconds
            additional_labels: Additional labels for the data
            send_to_loki: Whether to send to Loki
            send_to_prometheus: Whether to send to Prometheus
            
        Returns:
            Dictionary with success status for each service
        """
        results = {}
        
        # Send to Loki for detailed logging
        if send_to_loki and self.loki_client:
            try:
                results['loki'] = self.loki_client.send_time_interval_log(
                    game_type=game_type,
                    table=table,
                    round_id=round_id,
                    interval_type=interval_type,
                    duration=duration,
                    additional_labels=additional_labels
                )
            except Exception as e:
                logger.error(f"Error sending to Loki: {e}")
                results['loki'] = False
        
        # Send to Prometheus for metrics
        if send_to_prometheus and self.prometheus_client:
            try:
                results['prometheus'] = self.prometheus_client.send_time_interval_metric(
                    metric_name="time_interval_duration",
                    duration=duration,
                    game_type=game_type,
                    table=table,
                    round_id=round_id,
                    interval_type=interval_type,
                    additional_labels=additional_labels
                )
            except Exception as e:
                logger.error(f"Error sending to Prometheus: {e}")
                results['prometheus'] = False
        
        return results
    
    def store_batch_intervals(self,
                            intervals: List[Dict[str, Any]],
                            send_to_loki: bool = True,
                            send_to_prometheus: bool = True) -> Dict[str, bool]:
        """
        Store multiple time intervals in batch.
        
        Args:
            intervals: List of interval dictionaries
            send_to_loki: Whether to send to Loki
            send_to_prometheus: Whether to send to Prometheus
            
        Returns:
            Dictionary with success status for each service
        """
        results = {}
        
        # Send to Loki for detailed logging
        if send_to_loki and self.loki_client:
            try:
                # Prepare log entries for Loki
                log_entries = []
                for interval in intervals:
                    log_entry = {
                        'game_type': interval['game_type'],
                        'table': interval['table'],
                        'round_id': interval['round_id'],
                        'interval_type': interval['interval_type'],
                        'duration': interval['duration'],
                        'additional_labels': interval.get('additional_labels')
                    }
                    log_entries.append(log_entry)
                
                results['loki'] = self.loki_client.send_batch_logs(log_entries)
            except Exception as e:
                logger.error(f"Error sending batch to Loki: {e}")
                results['loki'] = False
        
        # Send to Prometheus for metrics
        if send_to_prometheus and self.prometheus_client:
            try:
                # Prepare metrics for Prometheus
                metrics = []
                for interval in intervals:
                    metric = {
                        'metric_name': 'time_interval_duration',
                        'duration': interval['duration'],
                        'game_type': interval['game_type'],
                        'table': interval['table'],
                        'round_id': interval['round_id'],
                        'interval_type': interval['interval_type'],
                        'additional_labels': interval.get('additional_labels')
                    }
                    metrics.append(metric)
                
                results['prometheus'] = self.prometheus_client.send_batch_metrics(metrics)
            except Exception as e:
                logger.error(f"Error sending batch to Prometheus: {e}")
                results['prometheus'] = False
        
        return results
    
    def store_error(self,
                   game_type: str,
                   table: str,
                   round_id: str,
                   error_message: str,
                   error_code: Optional[str] = None,
                   send_to_loki: bool = True) -> Dict[str, bool]:
        """
        Store error information to telemetry servers.
        
        Args:
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            error_message: Error message
            error_code: Optional error code
            send_to_loki: Whether to send to Loki
            
        Returns:
            Dictionary with success status for each service
        """
        results = {}
        
        # Send error to Loki (errors are typically logged, not metered)
        if send_to_loki and self.loki_client:
            try:
                results['loki'] = self.loki_client.send_error_log(
                    game_type=game_type,
                    table=table,
                    round_id=round_id,
                    error_message=error_message,
                    error_code=error_code
                )
            except Exception as e:
                logger.error(f"Error sending error to Loki: {e}")
                results['loki'] = False
        
        return results
    
    def store_counter_metric(self,
                           metric_name: str,
                           value: float,
                           game_type: str,
                           table: str,
                           additional_labels: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Store counter metric to Prometheus.
        
        Args:
            metric_name: Name of the counter metric
            value: Counter value
            game_type: Type of game
            table: Table identifier
            additional_labels: Additional labels
            
        Returns:
            Dictionary with success status for each service
        """
        results = {}
        
        if self.prometheus_client:
            try:
                results['prometheus'] = self.prometheus_client.send_counter_metric(
                    metric_name=metric_name,
                    value=value,
                    game_type=game_type,
                    table=table,
                    additional_labels=additional_labels
                )
            except Exception as e:
                logger.error(f"Error sending counter metric: {e}")
                results['prometheus'] = False
        
        return results
    
    def store_gauge_metric(self,
                          metric_name: str,
                          value: float,
                          game_type: str,
                          table: str,
                          additional_labels: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Store gauge metric to Prometheus.
        
        Args:
            metric_name: Name of the gauge metric
            value: Gauge value
            game_type: Type of game
            table: Table identifier
            additional_labels: Additional labels
            
        Returns:
            Dictionary with success status for each service
        """
        results = {}
        
        if self.prometheus_client:
            try:
                results['prometheus'] = self.prometheus_client.send_gauge_metric(
                    metric_name=metric_name,
                    value=value,
                    game_type=game_type,
                    table=table,
                    additional_labels=additional_labels
                )
            except Exception as e:
                logger.error(f"Error sending gauge metric: {e}")
                results['prometheus'] = False
        
        return results
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to all configured telemetry servers.
        
        Returns:
            Dictionary with connection test results for each service
        """
        results = {}
        
        if self.loki_client:
            try:
                results['loki'] = self.loki_client.test_connection()
            except Exception as e:
                logger.error(f"Loki connection test failed: {e}")
                results['loki'] = False
        
        if self.prometheus_client:
            try:
                results['prometheus'] = self.prometheus_client.test_connection()
            except Exception as e:
                logger.error(f"Prometheus connection test failed: {e}")
                results['prometheus'] = False
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information about the telemetry storage.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'loki_configured': self.loki_client is not None,
            'prometheus_configured': self.prometheus_client is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Test connections
        connection_results = self.test_connections()
        status.update(connection_results)
        
        return status
