-- Database Schema for AI Voice Chatbot
-- Run this once in the Supabase SQL editor

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    face_embedding JSONB
);

-- 2. Threads Table
CREATE TABLE IF NOT EXISTS threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Create index for quick thread lookups by user
CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);

-- 3. Messages Table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    role TEXT CHECK (role IN ('user', 'assistant')) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Create index for quick message history queries by thread
CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- 5. Permissive Policies for now
-- TODO(teammate): Tighten policies to restrict access based on authenticated user IDs prior to production deployment.
CREATE POLICY "Permissive access to users table" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Permissive access to threads table" ON threads FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Permissive access to messages table" ON messages FOR ALL USING (true) WITH CHECK (true);
