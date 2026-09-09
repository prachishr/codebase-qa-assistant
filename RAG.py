import os
from dotenv import load_dotenv 
load_dotenv(r"D:\Codebase-QA-Assistant\.venv\.env")
from groq import Groq

from retrieval import search_repository


MODEL_NAME = "openai/gpt-oss-20b"


def retrieve_documents(question, k=5):
    return search_repository(question, k=k)


def generate_answer(question):

    results = retrieve_documents(question)

    context_parts = []

    for result in results:

        file_name = result.metadata.get(
            "file",
            "Unknown"
        )

        content = result.page_content

        context_parts.append(
            f"FILE: {file_name}\n"
            f"CONTENT:\n{content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Please check your .env file."
        )

    client = Groq(api_key=api_key)

    system_prompt = """
You are a Codebase QA Assistant.

Your job is to answer questions about a software repository
using ONLY the provided repository context.

Rules:

1. Use the provided context to answer the question.
2. Do not invent information that is not present in the context.
3. If the answer cannot be found in the context, say:
   "I could not find enough information in the repository."
4. Explain technical concepts clearly.
5. Mention relevant file names when possible.
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

    return answer, results


if __name__ == "__main__":

    question = input(
        "\nAsk a question about the repository: "
    )

    answer, results = generate_answer(question)

    print("\n" + "=" * 70)
    print("ANSWER")
    print("=" * 70)

    print(answer)

    print("\n" + "=" * 70)
    print("SOURCES")
    print("=" * 70)

    for i, result in enumerate(results, start=1):

        print(
            f"{i}. "
            f"{result.metadata.get('file', 'Unknown')}"
        )