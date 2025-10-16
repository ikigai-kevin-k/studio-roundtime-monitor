"""
Loki client for sending log data to remote Loki server.

This client handles sending time interval monitoring data as structured logs
to the telemetry infrastructure's Loki service.
"""

import requests
import time
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class LokiClient:
    """
    Client for sending monitoring data to Loki server.
    
    Based on telemetry project's Loki integration patterns.
    """
    
    def __init__(self, loki_url: str, instance_id: str = "studio-roundtime-monitor"):
        """
        Initialize Loki client.
        
        Args:
            loki_url: URL of the Loki server (e.g., "http://100.64.0.113:3100")
            instance_id: Instance identifier for this monitor
        """
        self.loki_url = f"{loki_url.rstrip('/')}/loki/api/v1/push"
        self.instance_id = instance_id
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def send_time_interval_log(self, 
                             game_type: str,
                             table: str,
                             round_id: str,
                             interval_type: str,
                             duration: float,
                             additional_labels: Optional[Dict[str, str]] = None) -> bool:
        """
        Send time interval data as a log entry to Loki.
        
        Args:
            game_type: Type of game (roulette, sicbo, tableapi)
            table: Table identifier
            round_id: Round identifier
            interval_type: Type of interval (e.g., "start-to-betstop")
            duration: Duration in seconds
            additional_labels: Additional labels for the log entry
            
        Returns:
            True if successful, False otherwise
        """
        current_time = int(time.time() * 1000000000)  # nanoseconds
        
        # Create log message
        log_message = (f"Time interval: {interval_type} = {duration:.3f}s "
                      f"for {game_type} table {table} round {round_id}")
        
        # Prepare labels
        labels = {
            "job": "studio-roundtime-monitor",
            "instance": self.instance_id,
            "service": "time_monitor",
            "level": "INFO",
            "logger": "TimeMonitor",
            "game_type": game_type,
            "table": table,
            "round_id": round_id,
            "interval_type": interval_type
        }
        
        # Add additional labels if provided
        if additional_labels:
            labels.update(additional_labels)
        
        # Prepare the payload
        stream = {
            "stream": labels,
            "values": [
                [str(current_time), log_message]
            ]
        }
        
        payload = {"streams": [stream]}
        
        try:
            response = self.session.post(
                self.loki_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.debug(f"Successfully sent time interval log to Loki: {interval_type}")
                return True
            else:
                logger.error(f"Failed to send log to Loki: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending log to Loki: {e}")
            return False
    
    def send_batch_logs(self, log_entries: List[Dict[str, Any]]) -> bool:
        """
        Send multiple log entries in a single request.
        
        Args:
            log_entries: List of log entry dictionaries
            
        Returns:
            True if all entries sent successfully, False otherwise
        """
        current_time = int(time.time() * 1000000000)  # nanoseconds
        streams = []
        
        for i, entry in enumerate(log_entries):
            # Create log message
            log_message = (f"Time interval: {entry['interval_type']} = {entry['duration']:.3f}s "
                          f"for {entry['game_type']} table {entry['table']} round {entry['round_id']}")
            
            # Prepare labels
            labels = {
                "job": "studio-roundtime-monitor",
                "instance": self.instance_id,
                "service": "time_monitor",
                "level": "INFO",
                "logger": "TimeMonitor",
                "game_type": entry['game_type'],
                "table": entry['table'],
                "round_id": entry['round_id'],
                "interval_type": entry['interval_type']
            }
            
            # Add additional labels if provided
            if 'additional_labels' in entry and entry['additional_labels']:
                labels.update(entry['additional_labels'])
            
            stream = {
                "stream": labels,
                "values": [
                    [str(current_time + i * 1000000), log_message]  # Slight time offset for each entry
                ]
            }
            streams.append(stream)
        
        payload = {"streams": streams}
        
        try:
            response = self.session.post(
                self.loki_url,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 204:
                logger.debug(f"Successfully sent {len(log_entries)} log entries to Loki")
                return True
            else:
                logger.error(f"Failed to send batch logs to Loki: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending batch logs to Loki: {e}")
            return False
    
    def send_error_log(self, 
                      game_type: str,
                      table: str,
                      round_id: str,
                      error_message: str,
                      error_code: Optional[str] = None) -> bool:
        """
        Send error log to Loki.
        
        Args:
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            error_message: Error message
            error_code: Optional error code
            
        Returns:
            True if successful, False otherwise
        """
        current_time = int(time.time() * 1000000000)  # nanoseconds
        
        # Prepare labels
        labels = {
            "job": "studio-roundtime-monitor",
            "instance": self.instance_id,
            "service": "time_monitor",
            "level": "ERROR",
            "logger": "TimeMonitor",
            "game_type": game_type,
            "table": table,
            "round_id": round_id
        }
        
        if error_code:
            labels["error_code"] = error_code
        
        # Prepare the payload
        stream = {
            "stream": labels,
            "values": [
                [str(current_time), error_message]
            ]
        }
        
        payload = {"streams": [stream]}
        
        try:
            response = self.session.post(
                self.loki_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.debug(f"Successfully sent error log to Loki: {error_message}")
                return True
            else:
                logger.error(f"Failed to send error log to Loki: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending error log to Loki: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test connection to Loki server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Send a test log entry
            return self.send_time_interval_log(
                game_type="test",
                table="test_table",
                round_id="test_round",
                interval_type="test-interval",
                duration=1.0,
                additional_labels={"test": "true"}
            )
        except Exception as e:
            logger.error(f"Loki connection test failed: {e}")
            return False
