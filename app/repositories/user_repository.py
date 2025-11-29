"""
User data access layer using raw SQL
"""
import logging
import uuid
from typing import Optional, Dict, Any
from app.database import db
from app.utils.errors import UserNotFoundError

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user operations"""
    
    @staticmethod
    def get_or_create_user(user_id: str, username: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        """Get user by user_id or create if not exists"""
        try:
            # Try to get existing user
            query = "SELECT * FROM users WHERE user_id = %s"
            result = db.execute_query(query, (user_id,))
            
            if result:
                logger.info(f"User found: {user_id}")
                return result[0]
            
            # Create new user
            query = """
                INSERT INTO users (user_id, username, email)
                VALUES (%s, %s, %s)
            """
            user_id_db = db.execute_insert(query, (user_id, username, email))
            
            # Fetch created user
            query = "SELECT * FROM users WHERE id = %s"
            result = db.execute_query(query, (user_id_db,))
            
            logger.info(f"User created: {user_id}")
            return result[0]
            
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            raise
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Dict[str, Any]:
        """Get user by external user_id"""
        query = "SELECT * FROM users WHERE user_id = %s"
        result = db.execute_query(query, (user_id,))
        
        if not result:
            raise UserNotFoundError(user_id)
        
        return result[0]
    
    @staticmethod
    def get_user_by_db_id(user_db_id: int) -> Dict[str, Any]:
        """Get user by database ID"""
        query = "SELECT * FROM users WHERE id = %s"
        result = db.execute_query(query, (user_db_id,))
        
        if not result:
            raise UserNotFoundError(f"User with DB ID {user_db_id} not found")
        
        return result[0]
