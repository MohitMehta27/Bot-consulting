"""
Conversation data access layer using raw SQL
"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from app.database import db
from app.utils.errors import ConversationNotFoundError

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Repository for conversation operations"""
    
    @staticmethod
    def create_conversation(
        user_db_id: int,
        mode: str = "open_chat",
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation"""
        try:
            conversation_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO conversations (conversation_id, user_id, title, mode, status)
                VALUES (%s, %s, %s, %s, 'active')
            """
            conv_db_id = db.execute_insert(query, (conversation_id, user_db_id, title, mode))
            
            # Fetch created conversation
            query = "SELECT * FROM conversations WHERE id = %s"
            result = db.execute_query(query, (conv_db_id,))
            
            logger.info(f"Conversation created: {conversation_id}")
            return result[0]
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    @staticmethod
    def get_conversation_by_id(conversation_id: str) -> Dict[str, Any]:
        """Get conversation by conversation_id"""
        query = "SELECT * FROM conversations WHERE conversation_id = %s AND status != 'deleted'"
        result = db.execute_query(query, (conversation_id,))
        
        if not result:
            raise ConversationNotFoundError(conversation_id)
        
        return result[0]
    
    @staticmethod
    def get_conversation_by_db_id(conv_db_id: int) -> Dict[str, Any]:
        """Get conversation by database ID"""
        query = "SELECT * FROM conversations WHERE id = %s AND status != 'deleted'"
        result = db.execute_query(query, (conv_db_id,))
        
        if not result:
            raise ConversationNotFoundError(f"Conversation with DB ID {conv_db_id} not found")
        
        return result[0]
    
    @staticmethod
    def list_conversations(
        user_db_id: int,
        page: int = 1,
        limit: int = 10
    ) -> tuple[List[Dict[str, Any]], int]:
        """List conversations for a user with pagination"""
        offset = (page - 1) * limit
        
        # Get conversations
        query = """
            SELECT * FROM conversations
            WHERE user_id = %s AND status = 'active'
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """
        conversations = db.execute_query(query, (user_db_id, limit, offset))
        
        # Get total count
        count_query = """
            SELECT COUNT(*) as total FROM conversations
            WHERE user_id = %s AND status = 'active'
        """
        total_result = db.execute_query(count_query, (user_db_id,))
        total = total_result[0]['total'] if total_result else 0
        
        return conversations, total
    
    @staticmethod
    def get_latest_active_conversation_for_user(user_db_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recently updated active conversation for a user"""
        query = """
            SELECT * FROM conversations
            WHERE user_id = %s AND status = 'active'
            ORDER BY updated_at DESC
            LIMIT 1
        """
        result = db.execute_query(query, (user_db_id,))
        return result[0] if result else None
    
    @staticmethod
    def update_conversation_stats(conv_db_id: int, tokens: int, message_count: int):
        """Update conversation token and message counts"""
        query = """
            UPDATE conversations
            SET total_tokens = total_tokens + %s,
                total_messages = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        db.execute_update(query, (tokens, message_count, conv_db_id))
    
    @staticmethod
    def delete_conversation(conversation_id: str):
        """Soft delete a conversation"""
        query = """
            UPDATE conversations
            SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = %s
        """
        db.execute_update(query, (conversation_id,))
        logger.info(f"Conversation deleted: {conversation_id}")
    
    @staticmethod
    def link_document(conv_db_id: int, doc_db_id: int):
        """Link a document to a conversation"""
        query = """
            INSERT INTO conversation_documents (conversation_id, document_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE id = id
        """
        db.execute_insert(query, (conv_db_id, doc_db_id))
    
    @staticmethod
    def get_linked_documents(conv_db_id: int) -> List[Dict[str, Any]]:
        """Get all documents linked to a conversation"""
        query = """
            SELECT d.* FROM documents d
            INNER JOIN conversation_documents cd ON d.id = cd.document_id
            WHERE cd.conversation_id = %s
        """
        return db.execute_query(query, (conv_db_id,))
