import os
import json
import psycopg2
from dotenv import load_dotenv


load_dotenv(override=True)


DB_HOST = "aws-0-ap-northeast-2.pooler.supabase.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres.xpcconabdsyimyfmibtb"


def get_connection():
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise ValueError(
            "DB_PASSWORD not found. Add it to your .env file or Streamlit secrets."
        )

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=password,
        sslmode="require"
    )


# ============================================================
# Database Initialization
# ============================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Conversations
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT,
            title TEXT NOT NULL,
            repository_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # --------------------------------------------------------
    # Add user_id to existing installations
    # --------------------------------------------------------

    cursor.execute(
        """
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS user_id TEXT;
        """
    )

    # --------------------------------------------------------
    # Messages
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id BIGSERIAL PRIMARY KEY,
            conversation_id BIGINT NOT NULL
                REFERENCES conversations(id)
                ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            source_files JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # --------------------------------------------------------
    # Index for faster user-specific conversation lookup
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id
        ON conversations(user_id);
        """
    )

    connection.commit()

    cursor.close()
    connection.close()


# ============================================================
# Conversations
# ============================================================

def create_conversation(
    user_id,
    title="New Conversation",
    repository_url=""
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO conversations (
            user_id,
            title,
            repository_url
        )
        VALUES (%s, %s, %s)
        RETURNING id;
        """,
        (
            user_id,
            title,
            repository_url
        )
    )

    conversation_id = cursor.fetchone()[0]

    connection.commit()

    cursor.close()
    connection.close()

    return conversation_id


def update_conversation(
    user_id,
    conversation_id,
    title=None,
    repository_url=None
):

    connection = get_connection()
    cursor = connection.cursor()

    if title is not None and repository_url is not None:

        cursor.execute(
            """
            UPDATE conversations
            SET title = %s,
                repository_url = %s
            WHERE id = %s
              AND user_id = %s;
            """,
            (
                title,
                repository_url,
                conversation_id,
                user_id
            )
        )

    elif title is not None:

        cursor.execute(
            """
            UPDATE conversations
            SET title = %s
            WHERE id = %s
              AND user_id = %s;
            """,
            (
                title,
                conversation_id,
                user_id
            )
        )

    elif repository_url is not None:

        cursor.execute(
            """
            UPDATE conversations
            SET repository_url = %s
            WHERE id = %s
              AND user_id = %s;
            """,
            (
                repository_url,
                conversation_id,
                user_id
            )
        )

    connection.commit()

    cursor.close()
    connection.close()


# ============================================================
# Messages
# ============================================================

def save_message(
    user_id,
    conversation_id,
    role,
    content,
    source_files=None
):

    connection = get_connection()
    cursor = connection.cursor()

    if source_files is None:
        source_files = []

    # --------------------------------------------------------
    # Make sure the conversation belongs to this user
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = %s
          AND user_id = %s;
        """,
        (
            conversation_id,
            user_id
        )
    )

    conversation = cursor.fetchone()

    if conversation is None:

        cursor.close()
        connection.close()

        raise PermissionError(
            "You do not have access to this conversation."
        )

    # --------------------------------------------------------
    # Save message
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO messages (
            conversation_id,
            role,
            content,
            source_files
        )
        VALUES (%s, %s, %s, %s);
        """,
        (
            conversation_id,
            role,
            content,
            json.dumps(source_files)
        )
    )

    connection.commit()

    cursor.close()
    connection.close()


# ============================================================
# Get User Conversations
# ============================================================

def get_conversations(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            repository_url,
            created_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY created_at DESC;
        """,
        (user_id,)
    )

    conversations = cursor.fetchall()

    cursor.close()
    connection.close()

    return conversations


# ============================================================
# Get Messages
# ============================================================

def get_messages(
    user_id,
    conversation_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            m.role,
            m.content,
            m.source_files
        FROM messages m
        INNER JOIN conversations c
            ON m.conversation_id = c.id
        WHERE m.conversation_id = %s
          AND c.user_id = %s
        ORDER BY m.created_at ASC, m.id ASC;
        """,
        (
            conversation_id,
            user_id
        )
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    messages = []

    for role, content, source_files in rows:

        if source_files is None:
            source_files = []

        messages.append(
            {
                "role": role,
                "content": content,
                "sources": source_files
            }
        )

    return messages


# ============================================================
# Delete Conversation
# ============================================================

def delete_conversation(
    user_id,
    conversation_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM conversations
        WHERE id = %s
          AND user_id = %s;
        """,
        (
            conversation_id,
            user_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()