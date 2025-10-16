"""
Database storage implementation for Studio Round Time Monitor.

Provides database-based storage for time monitoring data with support for
SQLite, PostgreSQL, and MySQL databases.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
from sqlalchemy import create_engine, Column, Float, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid

from ..core.interval_calculator import IntervalData

logger = structlog.get_logger(__name__)

Base = declarative_base()

class IntervalRecord(Base):
    """SQLAlchemy model for interval records."""

    __tablename__ = "interval_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(Float, nullable=False)
    datetime = Column(DateTime, nullable=False)
    interval_type = Column(String(100), nullable=False)
    duration = Column(Float, nullable=False)
    game_type = Column(String(50), nullable=False)
    table = Column(String(50), nullable=False)
    round_id = Column(String(100), nullable=False)
    extra_data = Column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": self.datetime.isoformat(),
            "interval_type": self.interval_type,
            "duration": self.duration,
            "game_type": self.game_type,
            "table": self.table,
            "round_id": self.round_id,
            "metadata": self.extra_data or {}
        }

class DatabaseStorage:
    """
    Database-based storage for time monitoring data.

    Supports SQLite, PostgreSQL, and MySQL databases with automatic
    table creation and data persistence.
    """

    def __init__(self, database_url: str):
        """
        Initialize database storage.

        Args:
            database_url: Database connection URL
                - SQLite: sqlite:///path/to/database.db
                - PostgreSQL: postgresql://user:pass@host:port/dbname
                - MySQL: mysql://user:pass@host:port/dbname
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        Base.metadata.create_all(bind=self.engine)

        logger.info("Initialized database storage", database_url=database_url)

    def _get_session(self):
        """Get database session."""
        return self.SessionLocal()

    async def save_intervals(self, intervals: List[IntervalData]) -> None:
        """
        Save intervals to database.

        Args:
            intervals: List of interval data to save
        """
        if not intervals:
            return

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_intervals_sync, intervals)

            logger.info("Saved intervals to database", count=len(intervals))

        except Exception as e:
            logger.error("Error saving intervals to database", error=str(e))
            raise

    def _save_intervals_sync(self, intervals: List[IntervalData]) -> None:
        """Synchronous method to save intervals."""
        session = self._get_session()
        try:
            for interval in intervals:
                # Convert interval to database record
                record = IntervalRecord(
                    timestamp=interval.timestamp,
                    datetime=datetime.fromtimestamp(interval.timestamp),
                    interval_type=interval.interval_type.value,
                    duration=interval.duration,
                    game_type=interval.game_type,
                    table=interval.table,
                    round_id=interval.round_id,
                    extra_data=interval.metadata
                )
                session.add(record)

            session.commit()
        finally:
            session.close()

    async def load_intervals(self,
                           interval_type: Optional[str] = None,
                           game_type: Optional[str] = None,
                           table: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load intervals from database.

        Args:
            interval_type: Filter by interval type
            game_type: Filter by game type
            table: Filter by table
            limit: Maximum number of intervals to return

        Returns:
            List of interval dictionaries
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            intervals = await loop.run_in_executor(
                None, self._load_intervals_sync, interval_type, game_type, table, limit
            )

            logger.info("Loaded intervals from database",
                       count=len(intervals),
                       filters={
                           "interval_type": interval_type,
                           "game_type": game_type,
                           "table": table,
                           "limit": limit
                       })

            return intervals

        except Exception as e:
            logger.error("Error loading intervals from database", error=str(e))
            raise

    def _load_intervals_sync(self,
                           interval_type: Optional[str],
                           game_type: Optional[str],
                           table: Optional[str],
                           limit: Optional[int]) -> List[Dict[str, Any]]:
        """Synchronous method to load intervals."""
        session = self._get_session()
        try:
            query = session.query(IntervalRecord)

            # Apply filters
            if interval_type:
                query = query.filter(IntervalRecord.interval_type == interval_type)
            if game_type:
                query = query.filter(IntervalRecord.game_type == game_type)
            if table:
                query = query.filter(IntervalRecord.table == table)

            # Order by timestamp (most recent first)
            query = query.order_by(IntervalRecord.timestamp.desc())

            # Apply limit
            if limit is not None:
                query = query.limit(limit)

            # Execute query
            records = query.all()

            # Convert to dictionaries
            return [record.to_dict() for record in records]

        finally:
            session.close()

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

            import csv
            import aiofiles

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

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert intervals to dictionaries
            interval_dicts = [interval.to_dict() for interval in intervals]

            export_data = {
                "metadata": {
                    "exported": datetime.now().isoformat(),
                    "count": len(interval_dicts),
                    "description": "Exported Studio Round Time Monitor Data from Database"
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
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self._get_statistics_sync)

            return stats

        except Exception as e:
            logger.error("Error getting statistics from database", error=str(e))
            raise

    def _get_statistics_sync(self) -> Dict[str, Any]:
        """Synchronous method to get statistics."""
        session = self._get_session()
        try:
            # Get total count
            total_count = session.query(IntervalRecord).count()

            # Get interval type counts
            interval_type_counts = {}
            interval_types = session.query(IntervalRecord.interval_type).distinct().all()
            for (interval_type,) in interval_types:
                count = session.query(IntervalRecord).filter(
                    IntervalRecord.interval_type == interval_type
                ).count()
                interval_type_counts[interval_type] = count

            # Get game type counts
            game_type_counts = {}
            game_types = session.query(IntervalRecord.game_type).distinct().all()
            for (game_type,) in game_types:
                count = session.query(IntervalRecord).filter(
                    IntervalRecord.game_type == game_type
                ).count()
                game_type_counts[game_type] = count

            # Get table counts
            table_counts = {}
            tables = session.query(IntervalRecord.table).distinct().all()
            for (table,) in tables:
                count = session.query(IntervalRecord).filter(
                    IntervalRecord.table == table
                ).count()
                table_counts[table] = count

            # Get date range
            oldest_record = session.query(IntervalRecord).order_by(IntervalRecord.timestamp.asc()).first()
            newest_record = session.query(IntervalRecord).order_by(IntervalRecord.timestamp.desc()).first()

            date_range = {}
            if oldest_record:
                date_range["oldest"] = oldest_record.datetime.isoformat()
            if newest_record:
                date_range["newest"] = newest_record.datetime.isoformat()

            statistics = {
                "total_intervals": total_count,
                "interval_types": interval_type_counts,
                "game_types": game_type_counts,
                "tables": table_counts,
                "date_range": date_range,
                "database_url": self.database_url
            }

            return statistics

        finally:
            session.close()

    async def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """
        Clean up old data from database.

        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            removed_count = await loop.run_in_executor(
                None, self._cleanup_old_data_sync, days_to_keep
            )

            logger.info("Cleaned up old data from database",
                       removed_count=removed_count,
                       days_kept=days_to_keep)

        except Exception as e:
            logger.error("Error cleaning up old data from database", error=str(e))
            raise

    def _cleanup_old_data_sync(self, days_to_keep: int) -> int:
        """Synchronous method to cleanup old data."""
        session = self._get_session()
        try:
            cutoff_timestamp = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

            # Count records to be deleted
            count_before = session.query(IntervalRecord).count()

            # Delete old records
            session.query(IntervalRecord).filter(
                IntervalRecord.timestamp < cutoff_timestamp
            ).delete()

            session.commit()

            # Count remaining records
            count_after = session.query(IntervalRecord).count()

            return count_before - count_after

        finally:
            session.close()

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the database.

        Returns:
            Database information dictionary
        """
        try:
            session = self._get_session()
            try:
                # Get table info
                result = session.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in result.fetchall()]

                # Get record count
                total_records = session.query(IntervalRecord).count()

                return {
                    "database_url": self.database_url,
                    "tables": tables,
                    "total_records": total_records,
                    "engine": str(self.engine.url)
                }
            finally:
                session.close()

        except Exception as e:
            logger.error("Error getting database info", error=str(e))
            return {
                "database_url": self.database_url,
                "error": str(e)
            }
