"""
Prometheus client for sending metrics data to remote Prometheus Pushgateway.

This client handles sending time interval monitoring data as metrics
to the telemetry infrastructure's Prometheus service via Pushgateway.
"""

import requests
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class PrometheusClient:
    """
    Client for sending monitoring metrics to Prometheus via Pushgateway.
    
    Based on telemetry project's Prometheus integration patterns.
    """
    
    def __init__(self, pushgateway_url: str, job_name: str = "studio-roundtime-monitor"):
        """
        Initialize Prometheus client.
        
        Args:
            pushgateway_url: URL of the Prometheus Pushgateway (e.g., "http://100.64.0.113:9091")
            job_name: Job name for the metrics
        """
        self.pushgateway_url = f"{pushgateway_url.rstrip('/')}/metrics/job/{job_name}"
        self.job_name = job_name
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "text/plain"})
        
    def send_time_interval_metric(self,
                                metric_name: str,
                                duration: float,
                                game_type: str,
                                table: str,
                                round_id: str,
                                interval_type: str,
                                additional_labels: Optional[Dict[str, str]] = None) -> bool:
        """
        Send time interval data as a metric to Prometheus.
        
        Args:
            metric_name: Name of the metric (e.g., "time_interval_duration")
            duration: Duration in seconds
            game_type: Type of game (roulette, sicbo, tableapi)
            table: Table identifier
            round_id: Round identifier
            interval_type: Type of interval (e.g., "start-to-betstop")
            additional_labels: Additional labels for the metric
            
        Returns:
            True if successful, False otherwise
        """
        # Prepare labels
        labels = {
            "game_type": game_type,
            "table": table,
            "round_id": round_id,
            "interval_type": interval_type
        }
        
        # Add additional labels if provided
        if additional_labels:
            labels.update(additional_labels)
        
        # Format metric according to Prometheus format
        metric_data = self._format_metric(metric_name, duration, labels)
        
        try:
            response = self.session.post(
                self.pushgateway_url,
                data=metric_data,
                timeout=10
            )
            
            if response.ok:
                logger.debug(f"Successfully sent metric to Prometheus: {metric_name}")
                return True
            else:
                logger.error(f"Failed to send metric to Prometheus: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending metric to Prometheus: {e}")
            return False
    
    def send_batch_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Send multiple metrics in a single request.
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            True if all metrics sent successfully, False otherwise
        """
        metric_lines = []
        
        for metric in metrics:
            # Prepare labels
            labels = {
                "game_type": metric['game_type'],
                "table": metric['table'],
                "round_id": metric['round_id'],
                "interval_type": metric['interval_type']
            }
            
            # Add additional labels if provided
            if 'additional_labels' in metric and metric['additional_labels']:
                labels.update(metric['additional_labels'])
            
            # Format metric
            metric_line = self._format_metric(
                metric['metric_name'],
                metric['duration'],
                labels
            )
            metric_lines.append(metric_line)
        
        # Join all metrics with newlines
        metric_data = '\n'.join(metric_lines)
        
        try:
            response = self.session.post(
                self.pushgateway_url,
                data=metric_data,
                timeout=15
            )
            
            if response.ok:
                logger.debug(f"Successfully sent {len(metrics)} metrics to Prometheus")
                return True
            else:
                logger.error(f"Failed to send batch metrics to Prometheus: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending batch metrics to Prometheus: {e}")
            return False
    
    def send_counter_metric(self,
                          metric_name: str,
                          value: float,
                          game_type: str,
                          table: str,
                          additional_labels: Optional[Dict[str, str]] = None) -> bool:
        """
        Send counter metric to Prometheus.
        
        Args:
            metric_name: Name of the counter metric
            value: Counter value
            game_type: Type of game
            table: Table identifier
            additional_labels: Additional labels
            
        Returns:
            True if successful, False otherwise
        """
        labels = {
            "game_type": game_type,
            "table": table
        }
        
        if additional_labels:
            labels.update(additional_labels)
        
        metric_data = self._format_metric(metric_name, value, labels)
        
        try:
            response = self.session.post(
                self.pushgateway_url,
                data=metric_data,
                timeout=10
            )
            
            if response.ok:
                logger.debug(f"Successfully sent counter metric to Prometheus: {metric_name}")
                return True
            else:
                logger.error(f"Failed to send counter metric to Prometheus: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending counter metric to Prometheus: {e}")
            return False
    
    def send_gauge_metric(self,
                        metric_name: str,
                        value: float,
                        game_type: str,
                        table: str,
                        additional_labels: Optional[Dict[str, str]] = None) -> bool:
        """
        Send gauge metric to Prometheus.
        
        Args:
            metric_name: Name of the gauge metric
            value: Gauge value
            game_type: Type of game
            table: Table identifier
            additional_labels: Additional labels
            
        Returns:
            True if successful, False otherwise
        """
        labels = {
            "game_type": game_type,
            "table": table
        }
        
        if additional_labels:
            labels.update(additional_labels)
        
        metric_data = self._format_metric(metric_name, value, labels)
        
        try:
            response = self.session.post(
                self.pushgateway_url,
                data=metric_data,
                timeout=10
            )
            
            if response.ok:
                logger.debug(f"Successfully sent gauge metric to Prometheus: {metric_name}")
                return True
            else:
                logger.error(f"Failed to send gauge metric to Prometheus: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending gauge metric to Prometheus: {e}")
            return False
    
    def _format_metric(self, name: str, value: float, labels: Dict[str, str]) -> str:
        """
        Format metric according to Prometheus format.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Metric labels
            
        Returns:
            Formatted metric string
        """
        # Validate metric name
        if not name.replace('_', '').isalnum():
            raise ValueError(f"Invalid metric name: {name}")
        
        # Format labels
        if labels:
            label_pairs = []
            for key, val in labels.items():
                # Validate label name
                if not key.replace('_', '').isalnum():
                    raise ValueError(f"Invalid label name: {key}")
                # Escape label value
                escaped_val = str(val).replace('"', '\\"')
                label_pairs.append(f'{key}="{escaped_val}"')
            
            metric_line = f"{name}{{{','.join(label_pairs)}}} {value}\n"
        else:
            metric_line = f"{name} {value}\n"
        
        return metric_line
    
    def test_connection(self) -> bool:
        """
        Test connection to Prometheus Pushgateway.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Send a test metric
            return self.send_time_interval_metric(
                metric_name="test_metric",
                duration=1.0,
                game_type="test",
                table="test_table",
                round_id="test_round",
                interval_type="test-interval",
                additional_labels={"test": "true"}
            )
        except Exception as e:
            logger.error(f"Prometheus connection test failed: {e}")
            return False
