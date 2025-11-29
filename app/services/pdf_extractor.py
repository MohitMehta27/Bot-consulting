"""
PDF text extraction using OpenAI Vision API
"""
import logging
import base64
import io
from typing import List, Optional
from openai import OpenAI
from app.config import settings
from app.utils.errors import LLMServiceError

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDFs using OpenAI Vision API"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Use gpt-4o for vision (supports vision) or gpt-4-turbo
        self.vision_model = "gpt-4o"  # Supports vision natively
    
    def extract_text_from_pdf(self, pdf_bytes: bytes, max_pages: int = 10) -> str:
        """
        Extract text from PDF using OpenAI Vision API
        
        Args:
            pdf_bytes: PDF file content as bytes
            max_pages: Maximum number of pages to process (to control costs)
        
        Returns:
            Extracted text content
        """
        try:
            # Try using PyPDF2 to convert PDF pages to images
            try:
                from PyPDF2 import PdfReader
                from PIL import Image
                import io
                
                pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
                total_pages = len(pdf_reader.pages)
                pages_to_process = min(total_pages, max_pages)
                
                logger.info(f"Processing {pages_to_process} pages from PDF (total: {total_pages})")
                
                all_text = []
                
                for page_num in range(pages_to_process):
                    try:
                        page = pdf_reader.pages[page_num]
                        
                        # Try to extract text directly first (faster and cheaper)
                        page_text = page.extract_text()
                        
                        if page_text and len(page_text.strip()) > 50:
                            # Good text extraction, use it
                            all_text.append(f"--- Page {page_num + 1} ---\n{page_text}")
                            logger.info(f"Page {page_num + 1}: Extracted {len(page_text)} characters using PyPDF2")
                        else:
                            # Text extraction poor, use Vision API
                            logger.info(f"Page {page_num + 1}: Poor text extraction, using Vision API")
                            vision_text = self._extract_text_from_pdf_page_vision(pdf_bytes, page_num)
                            if vision_text:
                                all_text.append(f"--- Page {page_num + 1} ---\n{vision_text}")
                    
                    except Exception as page_error:
                        logger.warning(f"Error processing page {page_num + 1}: {page_error}")
                        # Try Vision API as fallback
                        try:
                            vision_text = self._extract_text_from_pdf_page_vision(pdf_bytes, page_num)
                            if vision_text:
                                all_text.append(f"--- Page {page_num + 1} ---\n{vision_text}")
                        except Exception as vision_error:
                            logger.error(f"Vision API also failed for page {page_num + 1}: {vision_error}")
                            continue
                
                if total_pages > max_pages:
                    all_text.append(f"\n[Note: Document has {total_pages} pages, only first {max_pages} processed]")
                
                extracted_text = "\n\n".join(all_text)
                logger.info(f"PDF extraction complete: {len(extracted_text)} characters extracted")
                return extracted_text
                
            except ImportError:
                logger.warning("PyPDF2 or PIL not available, using Vision API for all pages")
                # Fallback: use pdf2image if available
                return self._extract_text_using_pdf2image(pdf_bytes, max_pages)
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}", exc_info=True)
            raise LLMServiceError(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_text_from_pdf_page_vision(self, pdf_bytes: bytes, page_num: int) -> Optional[str]:
        """
        Extract text from a single PDF page using Vision API
        This is a fallback when direct text extraction fails
        """
        try:
            # Convert PDF page to image using pdf2image
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(pdf_bytes, first_page=page_num + 1, last_page=page_num + 1)
                
                if not images:
                    return None
                
                image = images[0]
                
                # Convert image to base64
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # Call Vision API
                response = self.client.chat.completions.create(
                    model=self.vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all text from this PDF page. Preserve the structure, formatting, and layout as much as possible. Include all visible text including headers, footers, and any text in tables or images."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4096
                )
                
                extracted_text = response.choices[0].message.content
                return extracted_text
                
            except ImportError:
                logger.warning("pdf2image not available. Install with: pip install pdf2image")
                logger.warning("Also need poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
                return None
        
        except Exception as e:
            logger.error(f"Error in Vision API extraction for page {page_num + 1}: {e}")
            return None
    
    def _extract_text_using_pdf2image(self, pdf_bytes: bytes, max_pages: int) -> str:
        """
        Extract text using pdf2image + Vision API for all pages
        """
        try:
            from pdf2image import convert_from_bytes
            
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=max_pages)
            all_text = []
            
            for idx, image in enumerate(images):
                try:
                    # Convert image to base64
                    buffered = io.BytesIO()
                    image.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    # Call Vision API
                    response = self.client.chat.completions.create(
                        model=self.vision_model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Extract all text from this PDF page. Preserve the structure, formatting, and layout as much as possible. Include all visible text including headers, footers, and any text in tables or images."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{img_base64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=4096
                    )
                    
                    page_text = response.choices[0].message.content
                    all_text.append(f"--- Page {idx + 1} ---\n{page_text}")
                    logger.info(f"Page {idx + 1}: Extracted {len(page_text)} characters using Vision API")
                
                except Exception as page_error:
                    logger.error(f"Error processing page {idx + 1} with Vision API: {page_error}")
                    continue
            
            return "\n\n".join(all_text)
        
        except ImportError:
            raise LLMServiceError("pdf2image not installed. Install with: pip install pdf2image pillow")
        except Exception as e:
            logger.error(f"Error in pdf2image extraction: {e}")
            raise

