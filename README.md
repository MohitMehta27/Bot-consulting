# BOT GPT - Conversational AI Backend

A production-grade conversational AI platform backend built with FastAPI, MySQL, and OpenAI.

## Features

- **Open Chat Mode**: Direct conversation with LLM without additional context
- **Grounded Chat (RAG) Mode**: Document-based conversations with retrieval-augmented generation
- **RESTful API**: Complete CRUD operations for conversations, messages, and documents
- **Context Management**: Intelligent token management and cost optimization
- **Scalable Architecture**: Clean separation of concerns with repository pattern

## Tech Stack

- **Framework**: FastAPI
- **Database**: MySQL (raw SQL queries)
- **LLM**: OpenAI API
- **Language**: Python 3.8+

## Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── database.py            # Database connection (raw SQL)
├── models/                # Data models (for reference)
├── schemas/               # Pydantic schemas for validation
├── api/v1/                # API routes
│   ├── conversations.py   # Conversation endpoints
│   ├── messages.py       # Message endpoints
│   └── documents.py      # Document endpoints
├── services/              # Business logic
│   ├── llm_service.py    # OpenAI integration
│   ├── rag_service.py    # RAG functionality
│   └── context_manager.py # Context/token management
├── repositories/          # Data access layer (raw SQL)
│   ├── user_repository.py
│   ├── conversation_repository.py
│   ├── message_repository.py
│   └── document_repository.py
└── utils/                 # Utilities
    ├── logger.py         # Logging setup
    └── errors.py         # Custom exceptions
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

1. Create MySQL database:
```sql
CREATE DATABASE bot_consulting;
```

2. Run the schema script:
```bash
# Copy and paste the SQL from database/schema.sql into your MySQL client
mysql -u root -p bot_consulting < database/schema.sql
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=bot_consulting

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Conversations

- `POST /api/v1/conversations` - Create new conversation
- `GET /api/v1/conversations` - List conversations (with pagination)
- `GET /api/v1/conversations/{conversation_id}` - Get conversation details
- `DELETE /api/v1/conversations/{conversation_id}` - Delete conversation

### Messages

- `POST /api/v1/conversations/{conversation_id}/messages` - Add message to conversation

### Documents

- `POST /api/v1/documents` - Upload document for RAG
- `GET /api/v1/documents/{document_id}` - Get document details

## Example Usage

### Create Open Chat Conversation

```bash
curl -X POST "http://localhost:8000/api/v1/conversations" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "first_message": "Hello, how are you?",
    "mode": "open_chat"
  }'
```

### Continue Conversation

```bash
curl -X POST "http://localhost:8000/api/v1/conversations/{conversation_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Tell me about Python"
  }'
```

### Create Grounded Chat (RAG)

```bash
# First, upload a document
curl -X POST "http://localhost:8000/api/v1/documents?user_id=user_001" \
  -F "file=@document.pdf"

# Then create conversation with document
curl -X POST "http://localhost:8000/api/v1/conversations" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "first_message": "What does the document say about X?",
    "mode": "grounded_chat",
    "document_ids": ["document_id_from_upload"]
  }'
```

## Testing

### Unit Tests

Run unit tests:

```bash
pytest tests/
```

### Web Interface

A simple HTML test interface is provided (`index.html`). To use it:

1. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

2. Open `index.html` in your web browser

3. The interface allows you to:
   - Create new conversations
   - Send messages
   - View conversation history
   - List all conversations

**Note**: If you encounter CORS issues, make sure the API is running and the URL in the HTML matches your server URL.

## Architecture Highlights

### Context Management

- **Sliding Window**: Keeps last N messages to manage context length
- **Token Estimation**: Rough estimation (1 token ≈ 4 characters)
- **Truncation**: Automatically truncates when context exceeds limits

### RAG Implementation

- **Document Chunking**: Splits documents into manageable chunks
- **FULLTEXT Search**: Uses MySQL FULLTEXT search for retrieval
- **Context Injection**: Injects retrieved chunks into LLM context

### Error Handling

- Custom exceptions for different error types
- Proper HTTP status codes
- Comprehensive logging

## Database Schema

Key tables:
- `users` - User information
- `conversations` - Conversation metadata
- `messages` - Individual messages
- `documents` - Uploaded documents
- `document_chunks` - Processed document chunks
- `conversation_documents` - Links conversations to documents

See `database/schema.sql` for complete schema.

## Logging

Logs are written to:
- Console (stdout)
- Daily rotating log files in `logs/` directory
- Automatic cleanup of logs older than 30 days

## Future Enhancements

- Vector embeddings for better RAG retrieval
- Conversation summarization for long contexts
- Rate limiting and authentication
- File storage in cloud (S3, etc.)
- WebSocket support for streaming responses
- Caching layer for common queries

## License

This project is part of a case study for BOT Consulting.
