
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from .ingestion import load_repository
from tree_sitter_language_pack import get_parser


CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".cs": "c_sharp",
    ".go": "go",
    ".php": "php",
    ".rb": "ruby",
}


def get_code_chunks(content, language, text_splitter):
    """
    Try AST-based code chunking with Tree-sitter.
    If the parser is unavailable, fall back to text-based chunking.
    """

    try:
        parser = get_parser(language)

        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)

        root = tree.root_node
        chunks = []

        interesting_nodes = {
            "function_declaration",
            "function_definition",
            "method_definition",
            "class_declaration",
            "class_definition",
            "method_declaration",
            "arrow_function",
        }

        def walk(node):
            if node.type in interesting_nodes:
                start = node.start_byte
                end = node.end_byte

                chunk = source_bytes[start:end].decode(
                    "utf-8",
                    errors="ignore"
                )

                if chunk.strip():
                    chunks.append(chunk)

                return

            for child in node.children:
                walk(child)

        walk(root)

        # If AST does not find useful structures,
        # use text-based chunking instead.
        if not chunks:
            chunks = text_splitter.split_text(content)
            return chunks, "code_fallback"

        return chunks, "ast_code"

    except Exception as exc:
        # Tree-sitter can fail if Windows blocks its DLL.
        print(
            f"[WARNING] Tree-sitter unavailable for "
            f"{language}. Using text-based chunking. "
            f"Reason: {exc}"
        )

        fallback_chunks = text_splitter.split_text(content)

        return fallback_chunks, "code_fallback"


def create_chunks(documents, repo_path):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = []

    repo_root = os.path.abspath(repo_path)

    for document in documents:

        file_name = document["file"]
        file_path = document["path"]
        content = document["content"]

        absolute_file_path = os.path.abspath(file_path)

        # --------------------------------------------------
        # README project overview
        # --------------------------------------------------

        is_root_readme = (
            absolute_file_path.lower()
            == os.path.join(
                repo_root,
                "README.md"
            ).lower()
        )

        if is_root_readme:

            overview = content[:2500]

            chunks.append({
                "content": overview,
                "type": "documentation",
                "file": file_name,
                "path": file_path,
                "source_priority": "high",
                "section": "project_overview"
            })

        # --------------------------------------------------
        # Code → AST-aware or fallback chunks
        # --------------------------------------------------

        if document["type"] == "code":

            extension = os.path.splitext(
                file_name
            )[1].lower()

            language = CODE_EXTENSIONS.get(extension)

            if language:

                code_chunks, chunking_method = get_code_chunks(
                    content,
                    language,
                    text_splitter
                )

                for chunk in code_chunks:

                    chunks.append({
                        "content": chunk,
                        "type": "code",
                        "file": file_name,
                        "path": file_path,
                        "source_priority": "normal",
                        "section": chunking_method
                    })

                continue

        # --------------------------------------------------
        # Documentation / Git history
        # --------------------------------------------------

        text_chunks = text_splitter.split_text(content)

        for chunk in text_chunks:

            if is_root_readme:
                source_priority = "high"

            elif document["type"] == "documentation":
                source_priority = "medium"

            else:
                source_priority = "low"

            chunks.append({
                "content": chunk,
                "type": document["type"],
                "file": file_name,
                "path": file_path,
                "source_priority": source_priority,
                "section": "general"
            })

    return chunks


if __name__ == "__main__":

    documents = load_repository("repo")

    chunks = create_chunks(
        documents,
        repo_path="repo"
    )

    print(f"Original documents: {len(documents)}")
    print(f"Total chunks: {len(chunks)}")

    ast_chunks = [
        chunk
        for chunk in chunks
        if chunk["section"] == "ast_code"
    ]

    fallback_chunks = [
        chunk
        for chunk in chunks
        if chunk["section"] == "code_fallback"
    ]

    print(f"AST code chunks: {len(ast_chunks)}")
    print(f"Fallback code chunks: {len(fallback_chunks)}")

    print("\nSample code chunks")
    print("------------------")

    for chunk in chunks:
        if chunk["type"] == "code":
            print(f"\nFile: {chunk['file']}")
            print(f"Section: {chunk['section']}")
            print(chunk["content"][:700])
            print("-" * 60)

            if chunk == chunks[-1]:
                break
