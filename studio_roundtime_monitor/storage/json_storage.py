"""
JSON storage implementation for Studio Round Time Monitor.

Provides JSON-based storage for time monitoring data with support for
appending new data and exporting to files.
"""

import json
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from ..core.interval_calculator import IntervalData

logger = structlog.get_logger(__name__)

class JSONStorage:
    """
    JSON-based storage for time monitoring data.

    Stores interval data in JSON format with support for appending
    new data and exporting to files.
    """

    def __init__(self, file_path: str):
        """
        Initialize JSON storage.

        Args:
            file_path: Path to the JSON storage file
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure file exists
        if not self.file_path.exists():
            self._initialize_file()

    def _initialize_file(self) -> None:
        """Initialize the storage file with empty structure."""
        initial_data = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0.0",
                "description": "Studio Round Time Monitor Data"
            },
            "intervals": []
        }

        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)

        logger.info("Initialized JSON storage file", file_path=str(self.file_path))

    async def save_intervals(self, intervals: List[IntervalData]) -> None:
        """
        Save intervals to JSON storage.

        Args:
            intervals: List of interval data to save
        """
        if not intervals:
            return

        try:
            # Read existing data
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]

            # Append new intervals
            data["intervals"].extend(interval_dicts)

            # Update metadata
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            data["metadata"]["total_intervals"] = len(data["intervals"])

            # Write back to file
            async with aiofiles.open(self.file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))

            logger.info("Saved intervals to JSON storage",
                       count=len(intervals),
                       total_intervals=len(data["intervals"]))

        except Exception as e:
            logger.error("Error saving intervals to JSON storage", error=str(e))
            raise

    async def load_intervals(self,
                           interval_type: Optional[str] = None,
                           game_type: Optional[str] = None,
                           table: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load intervals from JSON storage.

        Args:
            interval_type: Filter by interval type
            game_type: Filter by game type
            table: Filter by table
            limit: Maximum number of intervals to return

        Returns:
            List of interval dictionaries
        """
        try:
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

            intervals = data.get("intervals", [])

            # Apply filters
            if interval_type:
                intervals = [i for i in intervals if i.get("interval_type") == interval_type]

            if game_type:
                intervals = [i for i in intervals if i.get("game_type") == game_type]

            if table:
                intervals = [i for i in intervals if i.get("table") == table]

            # Apply limit
            if limit is not None:
                intervals = intervals[-limit:]

            logger.info("Loaded intervals from JSON storage",
                       count=len(intervals),
                       filters={
                           "interval_type": interval_type,
                           "game_type": game_type,
                           "table": table,
                           "limit": limit
                       })

            return intervals

        except Exception as e:
            logger.error("Error loading intervals from JSON storage", error=str(e))
            raise

    async def export_json(self, intervals: List[IntervalData], output_path: str) -> None:
        """
        Export intervals to a JSON file.

        Args:
            intervals: List of intervals to export
            output_path: Path to output file
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]

            export_data = {
                "metadata": {
                    "exported": datetime.now().isoformat(),
                    "count": len(interval_dicts),
                    "description": "Exported Studio Round Time Monitor Data"
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

    async def export_csv(self, intervals: List[IntervalData], output_path: str) -> None:
        """
        Export intervals to a CSV file.

        Args:
            intervals: List of intervals to export
            output_path: Path to output file
        """
        try:
            import csv

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

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored data.

        Returns:
            Statistics dictionary
        """
        try:
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

            intervals = data.get("intervals", [])

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
                "file_size": self.file_path.stat().st_size,
                "last_updated": data.get("metadata", {}).get("last_updated"),
                "created": data.get("metadata", {}).get("created")
            }

            return statistics

        except Exception as e:
            logger.error("Error getting statistics from JSON storage", error=str(e))
            raise

    async def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """
        Clean up old data from storage.

        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

            original_count = len(data.get("intervals", []))

            # Filter out old intervals
            data["intervals"] = [
                interval for interval in data.get("intervals", [])
                if interval.get("timestamp", 0) >= cutoff_date
            ]

            new_count = len(data["intervals"])
            removed_count = original_count - new_count

            # Update metadata
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            data["metadata"]["total_intervals"] = new_count

            # Write back to file
            async with aiofiles.open(self.file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))

            logger.info("Cleaned up old data from JSON storage",
                       removed_count=removed_count,
                       remaining_count=new_count,
                       days_kept=days_to_keep)

        except Exception as e:
            logger.error("Error cleaning up old data from JSON storage", error=str(e))
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
