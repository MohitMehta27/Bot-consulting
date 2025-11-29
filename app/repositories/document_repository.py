"""
Document data access layer using raw SQL
"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from app.database import db
from app.utils.errors import DocumentNotFoundError

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository for document operations"""
    
    @staticmethod
    def create_document(
        user_db_id: int,
        filename: str,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new document record"""
        try:
            document_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO documents (document_id, user_id, filename, file_path, file_type, file_size, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'processing')
            """
            doc_db_id = db.execute_insert(
                query,
                (document_id, user_db_id, filename, file_path, file_type, file_size)
            )
            
            # Fetch created document
            query = "SELECT * FROM documents WHERE id = %s"
            result = db.execute_query(query, (doc_db_id,))
            
            logger.info(f"Document created: {document_id}")
            return result[0]
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    @staticmethod
    def get_document_by_id(document_id: str) -> Dict[str, Any]:
        """Get document by document_id"""
        query = "SELECT * FROM documents WHERE document_id = %s"
        result = db.execute_query(query, (document_id,))
        
        if not result:
            raise DocumentNotFoundError(document_id)
        
        return result[0]
    
    @staticmethod
    def update_document_status(document_id: str, status: str):
        """Update document processing status"""
        query = """
            UPDATE documents
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE document_id = %s
        """
        db.execute_update(query, (status, document_id))
    
    @staticmethod
    def create_chunk(
        doc_db_id: int,
        chunk_text: str,
        chunk_index: int,
        token_count: int = 0
    ) -> Dict[str, Any]:
        """Create a document chunk"""
        try:
            chunk_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO document_chunks (chunk_id, document_id, chunk_text, chunk_index, token_count)
                VALUES (%s, %s, %s, %s, %s)
            """
            chunk_db_id = db.execute_insert(
                query,
                (chunk_id, doc_db_id, chunk_text, chunk_index, token_count)
            )
            
            # Fetch created chunk
            query = "SELECT * FROM document_chunks WHERE id = %s"
            result = db.execute_query(query, (chunk_db_id,))
            
            return result[0]
            
        except Exception as e:
            logger.error(f"Error creating chunk: {e}")
            raise
    
    @staticmethod
    def search_chunks(
        doc_db_ids: List[int],
        search_query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search document chunks using FULLTEXT search with fallback to LIKE"""
        if not doc_db_ids:
            return []
        
        # Create placeholders for IN clause
        placeholders = ','.join(['%s'] * len(doc_db_ids))
        
        # Try FULLTEXT search first
        try:
            query = f"""
                SELECT * FROM document_chunks
                WHERE document_id IN ({placeholders})
                AND MATCH(chunk_text) AGAINST(%s IN NATURAL LANGUAGE MODE)
                ORDER BY chunk_index ASC
                LIMIT %s
            """
            params = tuple(doc_db_ids) + (search_query, limit)
            results = db.execute_query(query, params)
            
            # If FULLTEXT returns results, use them
            if results:
                logger.info(f"FULLTEXT search found {len(results)} chunks")
                return results
        except Exception as e:
            logger.warning(f"FULLTEXT search failed: {e}, falling back to LIKE search")
        
        # Fallback to LIKE search if FULLTEXT fails or returns no results
        # Split query into keywords for better matching
        keywords = search_query.split()
        if not keywords:
            # If no keywords, just return first chunks
            query = f"""
                SELECT * FROM document_chunks
                WHERE document_id IN ({placeholders})
                ORDER BY chunk_index ASC
                LIMIT %s
            """
            params = tuple(doc_db_ids) + (limit,)
        else:
            # Build LIKE conditions for each keyword
            like_conditions = ' OR '.join(['chunk_text LIKE %s'] * len(keywords))
            query = f"""
                SELECT * FROM document_chunks
                WHERE document_id IN ({placeholders})
                AND ({like_conditions})
                ORDER BY chunk_index ASC
                LIMIT %s
            """
            keyword_params = tuple(['%' + keyword + '%' for keyword in keywords])
            params = tuple(doc_db_ids) + keyword_params + (limit,)
        
        results = db.execute_query(query, params)
        logger.info(f"LIKE search found {len(results)} chunks")
        return results
    
    @staticmethod
    def get_chunks_by_document(doc_db_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        query = """
            SELECT * FROM document_chunks
            WHERE document_id = %s
            ORDER BY chunk_index ASC
        """
        return db.execute_query(query, (doc_db_id,))
