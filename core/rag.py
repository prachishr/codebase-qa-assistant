
import os
from dotenv import load_dotenv
from groq import Groq

from .retrieval import search_repository

load_dotenv()

MODEL_NAME = "openai/gpt-oss-20b"


def retrieve_documents(question, k=5, index_path="faiss_index"):
    return search_repository(
        question,
        k=k,
        index_path=index_path
    )


def generate_answer(question, index_path="faiss_index"):

    results = retrieve_documents(
        question,
        index_path=index_path
    )

    if not results:
        return (
            "I could not find enough information in the repository.",
            []
        )

    context_parts = []

    for result in results:
        file_name = result.metadata.get("file", "Unknown")
        content = result.page_content

        context_parts.append(
            f"FILE: {file_name}\n"
            f"CONTENT:\n{content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Please check your .env file."
        )

    client = Groq(api_key=api_key)

    system_prompt = """
You are an expert Codebase QA Assistant.

Your responsibility is to explain and answer questions
about software repositories using the provided repository context.

STRICT RULES:

1. Use ONLY the information available in the provided repository context.

2. Never invent functions, classes, filenames, APIs,
   database tables, dependencies, or implementation details.

3. If the provided context does not contain enough
   information, clearly state:
   "I could not find enough information in the repository."

4. Distinguish between:
   - Information directly confirmed by the source code.
   - Information described in project documentation.

5. When explaining implementation details,
   prioritize actual source code over README descriptions.

6. Mention relevant filenames when explaining functionality.

7. For workflow questions, explain the sequence of operations
   only when the provided context supports that sequence.

8. If multiple files are involved, explain the responsibility
   of each file separately.

9. Do not claim that a file, function, or feature exists
   unless it appears in the provided context.

10. Keep explanations clear, accurate, and easy to understand.

11. If the context contains conflicting information,
    point out the conflict instead of choosing an unsupported answer.
12. Cite supporting files in your answers using this format:
    [Source: filename]

13. Every source citation must refer to a file
    actually included in the provided repository context.

14. Do not create fake citations or reference files
    that were not provided.
    
"""

    user_prompt = f"""
Repository Context:

{context}

Question:

{question}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        include_reasoning=False
    )

    answer = response.choices[0].message.content

    sources = [
        {
            "file": result.metadata.get("file", "Unknown"),
            "path": result.metadata.get("path", ""),
            "content": result.page_content
        }
        for result in results
    ]

    return answer, sources
