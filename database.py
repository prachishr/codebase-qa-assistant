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


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            repository_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

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

    connection.commit()

    cursor.close()
    connection.close()


def create_conversation(title="New Conversation", repository_url=""):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO conversations (title, repository_url)
        VALUES (%s, %s)
        RETURNING id;
        """,
        (title, repository_url)
    )

    conversation_id = cursor.fetchone()[0]

    connection.commit()

    cursor.close()
    connection.close()

    return conversation_id


def update_conversation(
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
            WHERE id = %s;
            """,
            (title, repository_url, conversation_id)
        )

    elif title is not None:

        cursor.execute(
            """
            UPDATE conversations
            SET title = %s
            WHERE id = %s;
            """,
            (title, conversation_id)
        )

    elif repository_url is not None:

        cursor.execute(
            """
            UPDATE conversations
            SET repository_url = %s
            WHERE id = %s;
            """,
            (repository_url, conversation_id)
        )

    connection.commit()

    cursor.close()
    connection.close()


def save_message(
    conversation_id,
    role,
    content,
    source_files=None
):
    connection = get_connection()
    cursor = connection.cursor()

    if source_files is None:
        source_files = []

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


def get_conversations():
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
        ORDER BY created_at DESC;
        """
    )

    conversations = cursor.fetchall()

    cursor.close()
    connection.close()

    return conversations


def get_messages(conversation_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            role,
            content,
            source_files
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC, id ASC;
        """,
        (conversation_id,)
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

def delete_conversation(conversation_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM conversations
        WHERE id = %s;
        """,
        (conversation_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()