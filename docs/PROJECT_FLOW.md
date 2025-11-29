# BOT GPT - Complete Project Flow

## Architecture Overview

```
┌─────────────┐
│   Client    │ (Postman, cURL, Frontend)
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌───────────────────────────────┐  │
│  │      API Layer (Routes)      │  │
│  │  - /conversations             │  │
│  │  - /messages                  │  │
│  │  - /documents                 │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │    Service Layer (Business)   │  │
│  │  - LLM Service                │  │
│  │  - RAG Service                │  │
│  │  - Context Manager            │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │  Repository Layer (Data)      │  │
│  │  - Conversation Repository    │  │
│  │  - Message Repository         │  │
│  │  - Document Repository        │  │
│  └───────────┬───────────────────┘  │
└──────────────┼──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         MySQL Database              │
│  - users                            │
│  - conversations                    │
│  - messages                         │
│  - documents                        │
│  - document_chunks                  │
└─────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      External Services              │
│  - OpenAI API (LLM)                 │
│  - (Optional: Vector DB for RAG)    │
└─────────────────────────────────────┘
```

---

## Flow 1: Create New Conversation (Open Chat Mode)

### Step-by-Step Flow:

1. **Client Request**
   ```
   POST /api/v1/conversations
   {
     "user_id": "user_001",
     "first_message": "Hello, how are you?",
     "mode": "open_chat"
   }
   ```

2. **API Layer** (`app/api/v1/conversations.py`)
   - Receives request
   - Validates payload using Pydantic schema
   - Calls service layer

3. **Service Layer** (`app/services/`)
   - **Conversation Service**:
     - Creates or retrieves user record
     - Creates new conversation record in DB
     - Generates unique conversation_id (UUID)

4. **Repository Layer** (`app/repositories/`)
   - **User Repository**: Get or create user
   - **Conversation Repository**: Insert new conversation
   - **Message Repository**: Insert first user message

5. **LLM Service** (`app/services/llm_service.py`)
   - Constructs messages array: `[{"role": "user", "content": "Hello, how are you?"}]`
   - Calls OpenAI API:
     ```python
     response = openai.ChatCompletion.create(
         model="gpt-3.5-turbo",
         messages=messages,
         temperature=0.7
     )
     ```
   - Receives assistant response
   - Calculates token usage

6. **Message Repository**
   - Saves assistant response to DB
   - Updates conversation token count

7. **Response to Client**
   ```json
   {
     "conversation_id": "conv_abc123",
     "message": {
       "role": "assistant",
       "content": "Hello! I'm doing well, thank you..."
     },
     "tokens_used": 45
   }
   ```

---

## Flow 2: Continue Existing Conversation (Open Chat Mode)

### Step-by-Step Flow:

1. **Client Request**
   ```
   POST /api/v1/conversations/{conversation_id}/messages
   {
     "content": "Tell me about Python"
   }
   ```

2. **API Layer**
   - Validates conversation_id exists
   - Validates request payload

3. **Repository Layer**
   - **Conversation Repository**: Fetch conversation by ID
   - **Message Repository**: Fetch all messages for conversation (ordered by sequence_number)

4. **Context Manager** (`app/services/context_manager.py`)
   - Retrieves conversation history
   - Checks total token count
   - If exceeds limit (e.g., 4000 tokens):
     - Option A: Use sliding window (keep last N messages)
     - Option B: Summarize old messages
     - Option C: Truncate oldest messages
   - Constructs optimized messages array

5. **LLM Service**
   - Adds new user message to context
   - Calls OpenAI API with full context
   - Receives response

6. **Repository Layer**
   - Saves new user message
   - Saves assistant response
   - Updates conversation metadata (total_tokens, total_messages)

7. **Response to Client**
   ```json
   {
     "message": {
       "role": "assistant",
       "content": "Python is a high-level programming language..."
     },
     "tokens_used": 120,
     "total_tokens": 165
   }
   ```

---

## Flow 3: Create Grounded Chat (RAG Mode)

### Step-by-Step Flow:

1. **Upload Document** (if not already uploaded)
   ```
   POST /api/v1/documents
   {
     "user_id": "user_001",
     "filename": "knowledge_base.pdf",
     "file_data": "<base64_encoded_file>"
   }
   ```

2. **Document Processing**
   - **Document Repository**: Save document metadata
   - **RAG Service** (`app/services/rag_service.py`):
     - Extracts text from PDF
     - Chunks text into smaller pieces (e.g., 500 tokens each)
     - Stores chunks in `document_chunks` table
     - (Optional: Generate embeddings, store in vector DB)

3. **Create Conversation with Document**
   ```
   POST /api/v1/conversations
   {
     "user_id": "user_001",
     "first_message": "What does the document say about X?",
     "mode": "grounded_chat",
     "document_ids": ["doc_123"]
   }
   ```

4. **Link Conversation to Document**
   - **Repository**: Insert into `conversation_documents` table

---

## Flow 4: Continue Grounded Chat (RAG Mode)

### Step-by-Step Flow:

1. **Client Request**
   ```
   POST /api/v1/conversations/{conversation_id}/messages
   {
     "content": "Can you explain section 2.3?"
   }
   ```

2. **Repository Layer**
   - Fetch conversation (verify mode = "grounded_chat")
   - Fetch linked documents via `conversation_documents`
   - Fetch conversation message history

3. **RAG Service** (`app/services/rag_service.py`)
   - **Retrieval Step**:
     - Takes user's new message: "Can you explain section 2.3?"
     - Searches document chunks (using FULLTEXT search or simple keyword matching)
     - Retrieves top 3-5 most relevant chunks
     - Example query:
       ```sql
       SELECT chunk_text FROM document_chunks
       WHERE document_id IN (SELECT document_id FROM conversation_documents WHERE conversation_id = ?)
       AND MATCH(chunk_text) AGAINST('section 2.3' IN NATURAL LANGUAGE MODE)
       LIMIT 5
       ```

4. **Context Construction**
   - **Context Manager**:
     - Retrieves recent conversation history (last 10 messages)
     - Adds retrieved document chunks as context
     - Constructs system prompt:
       ```
       "You are a helpful assistant. Use the following context from documents to answer questions:
       
       [Retrieved Chunk 1]
       [Retrieved Chunk 2]
       ...
       
       Conversation history:
       [Recent messages]
       "
       ```

5. **LLM Service**
   - Calls OpenAI with:
     - System message with context
     - Conversation history
     - New user message
   - Receives grounded response

6. **Repository Layer**
   - Saves user message
   - Saves assistant response
   - Updates conversation stats

7. **Response to Client**
   ```json
   {
     "message": {
       "role": "assistant",
       "content": "According to section 2.3 of the document..."
     },
     "retrieved_chunks": 3,
     "tokens_used": 250
   }
   ```

---

## Flow 5: List Conversations

### Step-by-Step Flow:

1. **Client Request**
   ```
   GET /api/v1/conversations?user_id=user_001&page=1&limit=10
   ```

2. **API Layer**
   - Validates query parameters
   - Handles pagination

3. **Repository Layer**
   - **Conversation Repository**:
     ```sql
     SELECT * FROM conversations
     WHERE user_id = ? AND status = 'active'
     ORDER BY updated_at DESC
     LIMIT ? OFFSET ?
     ```

4. **Response to Client**
   ```json
   {
     "conversations": [
       {
         "conversation_id": "conv_abc123",
         "title": "Python Discussion",
         "mode": "open_chat",
         "total_messages": 5,
         "created_at": "2024-01-15T10:30:00Z"
       }
     ],
     "pagination": {
       "page": 1,
       "limit": 10,
       "total": 25
     }
   }
   ```

---

## Flow 6: Get Conversation Details

### Step-by-Step Flow:

1. **Client Request**
   ```
   GET /api/v1/conversations/{conversation_id}
   ```

2. **Repository Layer**
   - Fetch conversation metadata
   - Fetch all messages (ordered by sequence_number)

3. **Response to Client**
   ```json
   {
     "conversation_id": "conv_abc123",
     "title": "Python Discussion",
     "mode": "open_chat",
     "messages": [
       {
         "role": "user",
         "content": "Hello",
         "sequence_number": 1,
         "created_at": "2024-01-15T10:30:00Z"
       },
       {
         "role": "assistant",
         "content": "Hi there!",
         "sequence_number": 2,
         "created_at": "2024-01-15T10:30:05Z"
       }
     ],
     "total_tokens": 165
   }
   ```

---

## Flow 7: Delete Conversation

### Step-by-Step Flow:

1. **Client Request**
   ```
   DELETE /api/v1/conversations/{conversation_id}
   ```

2. **Repository Layer**
   - Soft delete: Update `status = 'deleted'`
   - OR hard delete: CASCADE delete (messages, conversation_documents)

3. **Response to Client**
   ```json
   {
     "message": "Conversation deleted successfully"
   }
   ```

---

## Key Design Decisions

### 1. **Context Management Strategy**
- **Sliding Window**: Keep last N messages (e.g., last 20 messages)
- **Summarization**: Summarize old messages when context gets too long
- **Token Counting**: Track tokens per message, calculate total before LLM call

### 2. **RAG Retrieval Strategy**
- **Simple Approach**: FULLTEXT search in MySQL (good enough for MVP)
- **Advanced Approach**: Vector embeddings + similarity search (future enhancement)

### 3. **Error Handling**
- **LLM API Failures**: Retry with exponential backoff
- **DB Failures**: Transaction rollback, return 500 error
- **Token Limit**: Return 400 error with message "Context too long, please start new conversation"

### 4. **Cost Optimization**
- Track tokens per conversation
- Use cheaper models (gpt-3.5-turbo) for simple queries
- Cache common responses
- Implement rate limiting

---

## Data Flow Summary

```
User Request
    ↓
API Route (Validation)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (DB Operations)
    ↓
MySQL Database
    ↓
Service Layer (LLM Call)
    ↓
OpenAI API
    ↓
Service Layer (Process Response)
    ↓
Repository Layer (Save Response)
    ↓
MySQL Database
    ↓
API Response to User
```

---

## Next Steps for Implementation

1. **Phase 1**: Basic CRUD operations
   - User creation/retrieval
   - Conversation creation
   - Message storage

2. **Phase 2**: LLM Integration
   - OpenAI API integration
   - Basic context management
   - Token tracking

3. **Phase 3**: RAG Implementation
   - Document upload
   - Chunking logic
   - Retrieval mechanism

4. **Phase 4**: Advanced Features
   - Context summarization
   - Error handling & retries
   - Caching
   - Rate limiting

