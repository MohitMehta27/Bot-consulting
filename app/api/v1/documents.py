"""
Document API endpoints for RAG
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from app.schemas.document import DocumentCreate, DocumentResponse
from app.repositories.user_repository import UserRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.conversation_repository import ConversationRepository
from app.services.rag_service import RAGService
from app.services.pdf_extractor import PDFExtractor
from app.utils.errors import DocumentNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize services
user_repo = UserRepository()
document_repo = DocumentRepository()
conversation_repo = ConversationRepository()
rag_service = RAGService()
pdf_extractor = PDFExtractor()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user_id: str,
    file: UploadFile = File(...),
    conversation_id: Optional[str] = None,
):
    """
    Upload a document for RAG functionality
    Note: This is a simplified version. In production, you'd want to:
    - Store files in cloud storage (S3, etc.)
    - Process PDFs properly with libraries like PyPDF2
    - Handle different file types
    """
    try:
        # Get or create user
        user = user_repo.get_or_create_user(user_id=user_id)
        user_db_id = user['id']
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # For now, we'll store a placeholder path
        # In production, upload to cloud storage
        file_path = f"uploads/{user_id}/{file.filename}"
        
        # Determine file type
        file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else None
        
        # Create document record
        document = document_repo.create_document(
            user_db_id=user_db_id,
            filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size
        )
        
        # Process document (extract text and chunk)
        try:
            text_content = ""
            if file_type == 'txt':
                text_content = file_content.decode('utf-8')
            elif file_type == 'pdf':
                # Use OpenAI Vision API to extract text from PDF
                logger.info(f"Extracting text from PDF {file.filename} using OpenAI Vision")
                try:
                    text_content = pdf_extractor.extract_text_from_pdf(file_content, max_pages=20)
                    if not text_content or len(text_content.strip()) < 10:
                        logger.warning(f"PDF {file.filename} extraction returned minimal text")
                except Exception as pdf_error:
                    logger.error(f"Error extracting text from PDF {file.filename}: {pdf_error}")
                    # Fallback: try basic decoding
                    try:
                        text_content = file_content.decode('utf-8', errors='ignore')
                        if len(text_content.strip()) < 100:
                            text_content = file_content.decode('latin-1', errors='ignore')
                    except Exception as decode_error:
                        logger.error(f"Fallback decoding also failed: {decode_error}")
            elif file_type in ['doc', 'docx']:
                # For Word documents, would need python-docx
                logger.warning(f"Word document processing not fully implemented for {file.filename}")
                text_content = file_content.decode('utf-8', errors='ignore')
            else:
                text_content = file_content.decode('utf-8', errors='ignore')
            
            if text_content and len(text_content.strip()) > 10:
                chunk_count = rag_service.process_document(
                    document_id=document['document_id'],
                    text_content=text_content
                )
                logger.info(f"Document {document['document_id']} processed: {chunk_count} chunks created")
            else:
                logger.warning(f"Document {document['document_id']} has no extractable text content")
                document_repo.update_document_status(document['document_id'], 'failed')
        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
            document_repo.update_document_status(document['document_id'], 'failed')
        
        # Optionally link document to a conversation for grounded RAG
        # If no conversation_id is provided, fall back to the user's latest active conversation
        if not conversation_id:
            try:
                latest_conv = conversation_repo.get_latest_active_conversation_for_user(user_db_id)
                if latest_conv:
                    conversation_id = latest_conv["conversation_id"]
                else:
                    logger.info(f"No active conversations found for user {user_id}; document not linked")
            except Exception as latest_error:
                logger.warning(f"Failed to find latest conversation for user {user_id}: {latest_error}")
        
        if conversation_id:
            try:
                conversation = conversation_repo.get_conversation_by_id(conversation_id)
                conv_db_id = conversation["id"]
                # Only link if the conversation belongs to the same user
                if conversation["user_id"] == user_db_id:
                    conversation_repo.link_document(conv_db_id, document["id"])
                    logger.info(
                        f"Linked document {document['document_id']} to conversation {conversation_id}"
                    )
                else:
                    logger.warning(
                        f"Conversation {conversation_id} does not belong to user {user_id}; skipping link"
                    )
            except Exception as link_error:
                logger.warning(f"Failed to link document {document['document_id']} to conversation {conversation_id}: {link_error}")
        
        return DocumentResponse(**document)
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """
    Get document details
    """
    try:
        document = document_repo.get_document_by_id(document_id)
        return DocumentResponse(**document)
        
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
