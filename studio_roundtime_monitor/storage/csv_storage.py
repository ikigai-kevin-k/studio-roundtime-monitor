"""
CSV storage implementation for Studio Round Time Monitor.

Provides CSV-based storage for time monitoring data with support for
appending new data and exporting to files.
"""

import csv
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from ..core.interval_calculator import IntervalData

logger = structlog.get_logger(__name__)

class CSVStorage:
    """
    CSV-based storage for time monitoring data.

    Stores interval data in CSV format with support for appending
    new data and exporting to files.
    """

    def __init__(self, file_path: str):
        """
        Initialize CSV storage.

        Args:
            file_path: Path to the CSV storage file
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure file exists with header
        if not self.file_path.exists():
            self._initialize_file()

    def _initialize_file(self) -> None:
        """Initialize the storage file with CSV header."""
        fieldnames = [
            "timestamp", "datetime", "interval_type", "duration",
            "game_type", "table", "round_id", "metadata"
        ]

        with open(self.file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

        logger.info("Initialized CSV storage file", file_path=str(self.file_path))

    async def save_intervals(self, intervals: List[IntervalData]) -> None:
        """
        Save intervals to CSV storage.

        Args:
            intervals: List of interval data to save
        """
        if not intervals:
            return

        try:
            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]

            # Append to CSV file
            async with aiofiles.open(self.file_path, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=interval_dicts[0].keys())
                for interval_dict in interval_dicts:
                    writer.writerow(interval_dict)

            logger.info("Saved intervals to CSV storage", count=len(intervals))

        except Exception as e:
            logger.error("Error saving intervals to CSV storage", error=str(e))
            raise

    async def load_intervals(self,
                           interval_type: Optional[str] = None,
                           game_type: Optional[str] = None,
                           table: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load intervals from CSV storage.

        Args:
            interval_type: Filter by interval type
            game_type: Filter by game type
            table: Filter by table
            limit: Maximum number of intervals to return

        Returns:
            List of interval dictionaries
        """
        try:
            intervals = []

            async with aiofiles.open(self.file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Apply filters
                    if interval_type and row.get("interval_type") != interval_type:
                        continue
                    if game_type and row.get("game_type") != game_type:
                        continue
                    if table and row.get("table") != table:
                        continue

                    # Convert string values back to appropriate types
                    row["timestamp"] = float(row["timestamp"])
                    row["duration"] = float(row["duration"])

                    intervals.append(row)

            # Apply limit (get most recent)
            if limit is not None:
                intervals = intervals[-limit:]

            logger.info("Loaded intervals from CSV storage",
                       count=len(intervals),
                       filters={
                           "interval_type": interval_type,
                           "game_type": game_type,
                           "table": table,
                           "limit": limit
                       })

            return intervals

        except Exception as e:
            logger.error("Error loading intervals from CSV storage", error=str(e))
            raise

    async def export_csv(self, intervals: List[IntervalData], output_path: str) -> None:
        """
        Export intervals to a CSV file.

        Args:
            intervals: List of intervals to export
            output_path: Path to output file
        """
        try:
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

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]

            export_data = {
                "metadata": {
                    "exported": datetime.now().isoformat(),
                    "count": len(interval_dicts),
                    "description": "Exported Studio Round Time Monitor Data from CSV"
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
        Get statistics about stored data.

        Returns:
            Statistics dictionary
        """
        try:
            intervals = []

            async with aiofiles.open(self.file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert string values back to appropriate types
                    row["timestamp"] = float(row["timestamp"])
                    row["duration"] = float(row["duration"])
                    intervals.append(row)

            # Calculate statistics
            interval_types = {}
            game_types = {}
            tables = {}

            for interval in intervals:
                # Count interval types
                interval_type = interval.get("interval_type", "unknown")
                interval_types[interval_type] = interval_types.get(interval_type, 0) + 1

                # Count game types
                game_type = interval.get("game_type", "unknown")
                game_types[game_type] = game_types.get(game_type, 0) + 1

                # Count tables
                table = interval.get("table", "unknown")
                tables[table] = tables.get(table, 0) + 1

            statistics = {
                "total_intervals": len(intervals),
                "interval_types": interval_types,
                "game_types": game_types,
                "tables": tables,
                "file_size": self.file_path.stat().st_size
            }

            return statistics

        except Exception as e:
            logger.error("Error getting statistics from CSV storage", error=str(e))
            raise

    async def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """
        Clean up old data from storage.

        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_timestamp = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

            # Read all intervals
            intervals = []
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["timestamp"] = float(row["timestamp"])
                    intervals.append(row)

            # Filter out old intervals
            filtered_intervals = [
                interval for interval in intervals
                if interval["timestamp"] >= cutoff_timestamp
            ]

            removed_count = len(intervals) - len(filtered_intervals)

            # Rewrite file with filtered data
            if filtered_intervals:
                fieldnames = filtered_intervals[0].keys()
                async with aiofiles.open(self.file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for interval in filtered_intervals:
                        writer.writerow(interval)
            else:
                # If no data to keep, reinitialize file
                self._initialize_file()

            logger.info("Cleaned up old data from CSV storage",
                       removed_count=removed_count,
                       remaining_count=len(filtered_intervals),
                       days_kept=days_to_keep)

        except Exception as e:
            logger.error("Error cleaning up old data from CSV storage", error=str(e))
            raise

    def get_file_info(self) -> Dict[str, Any]:
        """
        Get information about the storage file.

        Returns:
            File information dictionary
        """
        try:
            stat = self.file_path.stat()
            return {
                "path": str(self.file_path),
                "exists": self.file_path.exists(),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
        except Exception as e:
            logger.error("Error getting file info", error=str(e))
            return {
                "path": str(self.file_path),
                "exists": False,
                "error": str(e)
            }
