import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from ingestion import load_repository
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


def get_code_chunks(content, language):

    parser = get_parser(language)

    tree = parser.parse(
        content.encode("utf-8")
    )

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

            chunk = content.encode(
                "utf-8"
            )[start:end].decode(
                "utf-8",
                errors="ignore"
            )

            if chunk.strip():
                chunks.append(chunk)

            return

        for child in node.children:
            walk(child)

    walk(root)

    # If AST did not find useful structures,
    # fall back to the complete file.
    if not chunks:
        chunks = [content]

    return chunks


def create_chunks(documents):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = []

    repo_root = os.path.abspath("repo")

    for document in documents:

        file_name = document["file"]
        file_path = document["path"]
        content = document["content"]

        absolute_file_path = os.path.abspath(
            file_path
        )

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
        # Code → AST-aware chunks
        # --------------------------------------------------

        if document["type"] == "code":

            extension = os.path.splitext(
                file_name
            )[1].lower()

            language = CODE_EXTENSIONS.get(
                extension
            )

            if language:

                code_chunks = get_code_chunks(
                    content,
                    language
                )

                for chunk in code_chunks:

                    chunks.append({
                        "content": chunk,
                        "type": "code",
                        "file": file_name,
                        "path": file_path,
                        "source_priority": "normal",
                        "section": "ast_code"
                    })

                continue

        # --------------------------------------------------
        # Documentation / Git history
        # --------------------------------------------------

        text_chunks = text_splitter.split_text(
            content
        )

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

    chunks = create_chunks(documents)

    print(
        f"Original documents: {len(documents)}"
    )

    print(
        f"Total chunks: {len(chunks)}"
    )

    ast_chunks = [
        chunk
        for chunk in chunks
        if chunk["section"] == "ast_code"
    ]

    print(
        f"AST code chunks: {len(ast_chunks)}"
    )

    print("\nSample AST chunks")
    print("----------------")

    for chunk in ast_chunks[:5]:

        print(
            f"\nFile: {chunk['file']}"
        )

        print(
            f"Section: {chunk['section']}"
        )

        print(
            chunk["content"][:700]
        )

        print("-" * 60)