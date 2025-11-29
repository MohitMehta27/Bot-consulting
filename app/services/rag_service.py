"""
RAG (Retrieval-Augmented Generation) service
"""
import logging
from typing import List, Dict, Any, Optional
from app.repositories.document_repository import DocumentRepository
from app.repositories.conversation_repository import ConversationRepository
from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation"""
    
    def __init__(self):
        self.document_repo = DocumentRepository()
        self.conversation_repo = ConversationRepository()
        self.max_chunks = settings.MAX_RETRIEVAL_CHUNKS
    
    def retrieve_relevant_chunks(
        self,
        conversation_id: str,
        user_query: str
    ) -> List[str]:
        """
        Retrieve relevant document chunks for a user query
        
        Args:
            conversation_id: Conversation ID
            user_query: User's query
        
        Returns:
            List of chunk texts
        """
        try:
            # Get conversation
            conversation = self.conversation_repo.get_conversation_by_id(conversation_id)
            conv_db_id = conversation['id']
            
            # Get linked documents
            linked_docs = self.conversation_repo.get_linked_documents(conv_db_id)
            
            if not linked_docs:
                logger.warning(f"No documents linked to conversation {conversation_id}")
                return []
            
            # Get document IDs
            doc_db_ids = [doc['id'] for doc in linked_docs]
            
            # Search for relevant chunks
            chunks = self.document_repo.search_chunks(
                doc_db_ids=doc_db_ids,
                search_query=user_query,
                limit=self.max_chunks
            )
            
            # Extract chunk texts
            chunk_texts = [chunk['chunk_text'] for chunk in chunks]
            
            if not chunk_texts:
                logger.warning(f"No chunks found for query: {user_query[:50]}...")
                # Fallback: get first few chunks from linked documents
                for doc_db_id in doc_db_ids:
                    all_chunks = self.document_repo.get_chunks_by_document(doc_db_id)
                    if all_chunks:
                        # Get first few chunks as fallback
                        chunk_texts.extend([chunk['chunk_text'] for chunk in all_chunks[:3]])
                        logger.info(f"Using fallback: retrieved {len(all_chunks[:3])} chunks from document {doc_db_id}")
                        if len(chunk_texts) >= self.max_chunks:
                            break
            
            logger.info(f"Retrieved {len(chunk_texts)} chunks for query: {user_query[:50]}...")
            
            return chunk_texts[:self.max_chunks]  # Ensure we don't exceed limit
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
    
    def process_document(
        self,
        document_id: str,
        text_content: str,
        chunk_size: int = 500
    ) -> int:
        """
        Process document: chunk text and store chunks
        
        Args:
            document_id: Document ID
            text_content: Full text content of document
            chunk_size: Approximate tokens per chunk
        
        Returns:
            Number of chunks created
        """
        try:
            # Get document
            document = self.document_repo.get_document_by_id(document_id)
            doc_db_id = document['id']
            
            # Simple chunking: split by paragraphs, then by sentences if needed
            chunks = self._chunk_text(text_content, chunk_size)
            
            # Store chunks
            chunk_count = 0
            for idx, chunk_text in enumerate(chunks):
                token_count = len(chunk_text) // 4  # Rough estimate
                self.document_repo.create_chunk(
                    doc_db_id=doc_db_id,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    token_count=token_count
                )
                chunk_count += 1
            
            # Update document status
            self.document_repo.update_document_status(document_id, 'processed')
            
            logger.info(f"Processed document {document_id}: {chunk_count} chunks created")
            return chunk_count
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            self.document_repo.update_document_status(document_id, 'failed')
            raise
    
    def _chunk_text(self, text: str, target_tokens: int) -> List[str]:
        """
        Simple text chunking strategy
        Splits by paragraphs first, then by sentences if chunks are too large
        """
        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para) // 4  # Rough token estimate
            
            if para_size > target_tokens:
                # Paragraph is too large, split by sentences
                sentences = para.split('. ')
                for sentence in sentences:
                    sent_size = len(sentence) // 4
                    if current_size + sent_size > target_tokens and current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = [sentence]
                        current_size = sent_size
                    else:
                        current_chunk.append(sentence)
                        current_size += sent_size
            else:
                if current_size + para_size > target_tokens and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [para]
                    current_size = para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
