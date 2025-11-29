"""
Database connection and session management using raw SQL (pymysql)
"""
import pymysql
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager using raw SQL"""
    
    def __init__(self):
        self.connection: Optional[pymysql.Connection] = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            logger.info(f"Connected to MySQL database: {settings.DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        if not self.connection or not self.connection.open:
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT query and return last insert ID"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid


# Global database instance
db = Database()
