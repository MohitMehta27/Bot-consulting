-- =====================================================
-- BOT GPT Database Schema
-- Database: bot_consulting
-- =====================================================

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS bot_consulting;
USE bot_consulting;

-- =====================================================
-- Table: users
-- Stores user information
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'External user identifier (e.g., email, UUID)',
    username VARCHAR(255) NULL COMMENT 'Optional username',
    email VARCHAR(255) NULL COMMENT 'Optional email',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Table: conversations
-- Stores conversation metadata
-- =====================================================
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'External conversation identifier (UUID)',
    user_id INT NOT NULL COMMENT 'Foreign key to users table',
    title VARCHAR(500) NULL COMMENT 'Conversation title (can be auto-generated)',
    mode ENUM('open_chat', 'grounded_chat') DEFAULT 'open_chat' COMMENT 'Chat mode: open or RAG-based',
    status ENUM('active', 'archived', 'deleted') DEFAULT 'active',
    total_tokens INT DEFAULT 0 COMMENT 'Total tokens used in this conversation',
    total_messages INT DEFAULT 0 COMMENT 'Total message count',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_user_id (user_id),
    INDEX idx_mode (mode),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Table: messages
-- Stores individual messages in conversations
-- =====================================================
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'External message identifier (UUID)',
    conversation_id INT NOT NULL COMMENT 'Foreign key to conversations table',
    role ENUM('user', 'assistant', 'system') NOT NULL COMMENT 'Message role',
    content TEXT NOT NULL COMMENT 'Message content',
    tokens_used INT DEFAULT 0 COMMENT 'Tokens used for this message',
    sequence_number INT NOT NULL COMMENT 'Message order in conversation',
    metadata JSON NULL COMMENT 'Additional metadata (model used, temperature, etc.)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_message_id (message_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_sequence_number (conversation_id, sequence_number),
    INDEX idx_role (role),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Table: documents
-- Stores uploaded documents for RAG functionality
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'External document identifier (UUID)',
    user_id INT NOT NULL COMMENT 'Foreign key to users table',
    filename VARCHAR(500) NOT NULL COMMENT 'Original filename',
    file_path VARCHAR(1000) NULL COMMENT 'Storage path (if storing files)',
    file_type VARCHAR(50) NULL COMMENT 'File type (pdf, txt, docx, etc.)',
    file_size BIGINT NULL COMMENT 'File size in bytes',
    status ENUM('processing', 'processed', 'failed') DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Table: document_chunks
-- Stores processed chunks of documents for RAG retrieval
-- =====================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chunk_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'External chunk identifier (UUID)',
    document_id INT NOT NULL COMMENT 'Foreign key to documents table',
    chunk_text TEXT NOT NULL COMMENT 'Chunk content',
    chunk_index INT NOT NULL COMMENT 'Order of chunk in document',
    token_count INT DEFAULT 0 COMMENT 'Token count for this chunk',
    embedding_vector JSON NULL COMMENT 'Optional: embedding vector (if using vector search)',
    metadata JSON NULL COMMENT 'Additional chunk metadata',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    INDEX idx_chunk_id (chunk_id),
    INDEX idx_document_id (document_id),
    INDEX idx_chunk_index (document_id, chunk_index),
    FULLTEXT idx_fulltext_content (chunk_text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Table: conversation_documents
-- Junction table linking conversations to documents (many-to-many)
-- =====================================================
CREATE TABLE IF NOT EXISTS conversation_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL COMMENT 'Foreign key to conversations table',
    document_id INT NOT NULL COMMENT 'Foreign key to documents table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE KEY unique_conversation_document (conversation_id, document_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_document_id (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Table: conversation_summaries
-- Optional: Stores conversation summaries for context management
-- =====================================================
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL COMMENT 'Foreign key to conversations table',
    summary_text TEXT NOT NULL COMMENT 'Summary of conversation up to a point',
    message_count_covered INT NOT NULL COMMENT 'Number of messages covered by this summary',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Sample Data (Optional - for testing)
-- =====================================================

-- Insert a sample user
INSERT INTO users (user_id, username, email) 
VALUES ('user_001', 'test_user', 'test@example.com')
ON DUPLICATE KEY UPDATE username=username;

