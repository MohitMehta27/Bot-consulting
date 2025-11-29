"""
Message data access layer using raw SQL
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from app.database import db

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repository for message operations"""
    
    @staticmethod
    def create_message(
        conv_db_id: int,
        role: str,
        content: str,
        tokens_used: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new message"""
        try:
            message_id = str(uuid.uuid4())
            
            # Get next sequence number
            query = """
                SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                FROM messages
                WHERE conversation_id = %s
            """
            result = db.execute_query(query, (conv_db_id,))
            sequence_number = result[0]['next_seq'] if result else 1
            
            # Insert message
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            query = """
                INSERT INTO messages (message_id, conversation_id, role, content, tokens_used, sequence_number, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            msg_db_id = db.execute_insert(
                query,
                (message_id, conv_db_id, role, content, tokens_used, sequence_number, metadata_json)
            )
            
            # Fetch created message
            query = "SELECT * FROM messages WHERE id = %s"
            result = db.execute_query(query, (msg_db_id,))
            
            logger.info(f"Message created: {message_id}, sequence: {sequence_number}")
            return result[0]
            
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise
    
    @staticmethod
    def get_messages_by_conversation(conv_db_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a conversation ordered by sequence"""
        query = """
            SELECT * FROM messages
            WHERE conversation_id = %s
            ORDER BY sequence_number ASC
        """
        return db.execute_query(query, (conv_db_id,))
    
    @staticmethod
    def get_recent_messages(conv_db_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages for a conversation"""
        query = """
            SELECT * FROM messages
            WHERE conversation_id = %s
            ORDER BY sequence_number DESC
            LIMIT %s
        """
        messages = db.execute_query(query, (conv_db_id, limit))
        # Reverse to get chronological order
        return list(reversed(messages))
    
    @staticmethod
    def get_message_count(conv_db_id: int) -> int:
        """Get total message count for a conversation"""
        query = """
            SELECT COUNT(*) as count FROM messages
            WHERE conversation_id = %s
        """
        result = db.execute_query(query, (conv_db_id,))
        return result[0]['count'] if result else 0
