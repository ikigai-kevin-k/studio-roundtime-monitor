"""
Telemetry storage backend for Studio Round Time Monitor.

This module provides a storage backend that sends monitoring data to remote
telemetry servers (Loki and Prometheus) instead of storing locally.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from ..core.interval_calculator import IntervalData
from ..telemetry.telemetry_storage import TelemetryStorage

logger = structlog.get_logger(__name__)


class TelemetryStorageBackend:
    """
    Storage backend that sends monitoring data to remote telemetry servers.
    
    This backend replaces local database storage with telemetry infrastructure
    integration, sending data to Loki (for logs) and Prometheus (for metrics).
    """
    
    def __init__(self, 
                 loki_url: Optional[str] = None,
                 prometheus_url: Optional[str] = None,
                 instance_id: str = "studio-roundtime-monitor",
                 job_name: str = "studio-roundtime-monitor"):
        """
        Initialize telemetry storage backend.
        
        Args:
            loki_url: URL of the Loki server (e.g., "http://100.64.0.113:3100")
            prometheus_url: URL of the Prometheus Pushgateway (e.g., "http://100.64.0.113:9091")
            instance_id: Instance identifier for this monitor
            job_name: Job name for Prometheus metrics
        """
        self.telemetry_storage = TelemetryStorage(
            loki_url=loki_url,
            prometheus_url=prometheus_url,
            instance_id=instance_id,
            job_name=job_name
        )
        
        logger.info("Initialized telemetry storage backend",
                   loki_url=loki_url,
                   prometheus_url=prometheus_url,
                   instance_id=instance_id)
    
    async def save_intervals(self, intervals: List[IntervalData]) -> None:
        """
        Save intervals to telemetry servers.
        
        Args:
            intervals: List of interval data to save
        """
        if not intervals:
            return
        
        try:
            # Convert intervals to telemetry format
            telemetry_intervals = []
            for interval in intervals:
                telemetry_interval = {
                    'game_type': interval.game_type,
                    'table': interval.table,
                    'round_id': interval.round_id,
                    'interval_type': interval.interval_type.value,
                    'duration': interval.duration,
                    'additional_labels': interval.metadata or {}
                }
                telemetry_intervals.append(telemetry_interval)
            
            # Send to telemetry servers
            results = self.telemetry_storage.store_batch_intervals(telemetry_intervals)
            
            # Log results
            success_count = sum(1 for success in results.values() if success)
            total_services = len(results)
            
            logger.info("Saved intervals to telemetry servers",
                       count=len(intervals),
                       success_count=success_count,
                       total_services=total_services,
                       results=results)
            
            # Check if any service failed
            failed_services = [service for service, success in results.items() if not success]
            if failed_services:
                logger.warning("Some telemetry services failed",
                             failed_services=failed_services)
        
        except Exception as e:
            logger.error("Error saving intervals to telemetry servers", error=str(e))
            raise
    
    async def load_intervals(self,
                           interval_type: Optional[str] = None,
                           game_type: Optional[str] = None,
                           table: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load intervals from telemetry servers.
        
        Note: This method is not fully supported for telemetry storage as
        Loki and Prometheus are primarily for sending data, not querying historical data.
        This method returns an empty list as telemetry storage is write-only.
        
        Args:
            interval_type: Filter by interval type (not used)
            game_type: Filter by game type (not used)
            table: Filter by table (not used)
            limit: Maximum number of intervals to return (not used)
            
        Returns:
            Empty list (telemetry storage is write-only)
        """
        logger.warning("load_intervals not supported for telemetry storage - returning empty list")
        return []
    
    async def export_csv(self, intervals: List[IntervalData], output_path: str) -> None:
        """
        Export intervals to a CSV file.
        
        Args:
            intervals: List of intervals to export
            output_path: Path to output file
        """
        try:
            from pathlib import Path
            import csv
            import aiofiles
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if not intervals:
                logger.warning("No intervals to export to CSV")
                return
            
            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]
            
            # Get fieldnames from first interval
            fieldnames = interval_dicts[0].keys()
            
            async with aiofiles.open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for interval_dict in interval_dicts:
                    writer.writerow(interval_dict)
            
            logger.info("Exported intervals to CSV file",
                       count=len(intervals),
                       output_path=str(output_file))
        
        except Exception as e:
            logger.error("Error exporting intervals to CSV", error=str(e))
            raise
    
    async def export_json(self, intervals: List[IntervalData], output_path: str) -> None:
        """
        Export intervals to a JSON file.
        
        Args:
            intervals: List of intervals to export
            output_path: Path to output file
        """
        try:
            import json
            import aiofiles
            from pathlib import Path
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]
            
            export_data = {
                "metadata": {
                    "exported": datetime.now().isoformat(),
                    "count": len(interval_dicts),
                    "description": "Exported Studio Round Time Monitor Data from Telemetry Storage"
                },
                "intervals": interval_dicts
            }
            
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(export_data, indent=2, ensure_ascii=False))
            
            logger.info("Exported intervals to JSON file",
                       count=len(intervals),
                       output_path=str(output_file))
        
        except Exception as e:
            logger.error("Error exporting intervals to JSON", error=str(e))
            raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about telemetry storage.
        
        Returns:
            Statistics dictionary
        """
        try:
            status = self.telemetry_storage.get_status()
            
            statistics = {
                "storage_type": "telemetry",
                "loki_configured": status.get('loki_configured', False),
                "prometheus_configured": status.get('prometheus_configured', False),
                "loki_connected": status.get('loki', False),
                "prometheus_connected": status.get('prometheus', False),
                "timestamp": status.get('timestamp'),
                "description": "Telemetry storage backend - data sent to remote servers"
            }
            
            return statistics
        
        except Exception as e:
            logger.error("Error getting telemetry storage statistics", error=str(e))
            return {
                "storage_type": "telemetry",
                "error": str(e)
            }
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """
        Clean up old data from telemetry storage.
        
        Note: This method is not applicable for telemetry storage as data
        is sent to remote servers and managed by the telemetry infrastructure.
        
        Args:
            days_to_keep: Number of days of data to keep (not used)
        """
        logger.info("cleanup_old_data not applicable for telemetry storage - data managed by remote servers")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the telemetry storage.
        
        Returns:
            Storage information dictionary
        """
        try:
            status = self.telemetry_storage.get_status()
            
            return {
                "storage_type": "telemetry",
                "loki_configured": status.get('loki_configured', False),
                "prometheus_configured": status.get('prometheus_configured', False),
                "loki_connected": status.get('loki', False),
                "prometheus_connected": status.get('prometheus', False),
                "timestamp": status.get('timestamp'),
                "description": "Telemetry storage backend for remote data transmission"
            }
        
        except Exception as e:
            logger.error("Error getting telemetry storage info", error=str(e))
            return {
                "storage_type": "telemetry",
                "error": str(e)
            }
    
    async def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to telemetry servers.
        
        Returns:
            Dictionary with connection test results
        """
        try:
            results = self.telemetry_storage.test_connections()
            
            logger.info("Telemetry connection test results", results=results)
            
            return results
        
        except Exception as e:
            logger.error("Error testing telemetry connections", error=str(e))
            return {}
    
    def send_error(self, 
                  game_type: str,
                  table: str,
                  round_id: str,
                  error_message: str,
                  error_code: Optional[str] = None) -> Dict[str, bool]:
        """
        Send error information to telemetry servers.
        
        Args:
            game_type: Type of game
            table: Table identifier
            round_id: Round identifier
            error_message: Error message
            error_code: Optional error code
            
        Returns:
            Dictionary with success status for each service
        """
        try:
            results = self.telemetry_storage.store_error(
                game_type=game_type,
                table=table,
                round_id=round_id,
                error_message=error_message,
                error_code=error_code
            )
            
            logger.info("Sent error to telemetry servers", results=results)
            
            return results
        
        except Exception as e:
            logger.error("Error sending error to telemetry servers", error=str(e))
            return {}
    
    def send_counter_metric(self,
                           metric_name: str,
                           value: float,
                           game_type: str,
                           table: str,
                           additional_labels: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Send counter metric to Prometheus.
        
        Args:
            metric_name: Name of the counter metric
            value: Counter value
            game_type: Type of game
            table: Table identifier
            additional_labels: Additional labels
            
        Returns:
            Dictionary with success status for each service
        """
        try:
            results = self.telemetry_storage.store_counter_metric(
                metric_name=metric_name,
                value=value,
                game_type=game_type,
                table=table,
                additional_labels=additional_labels
            )
            
            logger.info("Sent counter metric to telemetry servers", results=results)
            
            return results
        
        except Exception as e:
            logger.error("Error sending counter metric to telemetry servers", error=str(e))
            return {}
    
    def send_gauge_metric(self,
                        metric_name: str,
                        value: float,
                        game_type: str,
                        table: str,
                        additional_labels: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Send gauge metric to Prometheus.
        
        Args:
            metric_name: Name of the gauge metric
            value: Gauge value
            game_type: Type of game
            table: Table identifier
            additional_labels: Additional labels
            
        Returns:
            Dictionary with success status for each service
        """
        try:
            results = self.telemetry_storage.store_gauge_metric(
                metric_name=metric_name,
                value=value,
                game_type=game_type,
                table=table,
                additional_labels=additional_labels
            )
            
            logger.info("Sent gauge metric to telemetry servers", results=results)
            
            return results
        
        except Exception as e:
            logger.error("Error sending gauge metric to telemetry servers", error=str(e))
            return {}
