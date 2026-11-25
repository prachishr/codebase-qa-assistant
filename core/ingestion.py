import os
from git import Repo


# Files that we want to analyze
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".cs",
    ".go",
    ".php",
    ".rb",
}


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "dist",
    "build",
    "coverage",
    "site-packages",
    "faiss_index"
}

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB


SENSITIVE_FILE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "id_dsa",
    "id_ecdsa",
    "credentials.json",
    "secrets.json",
    "service-account.json",
    "config.json"
}

SENSITIVE_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx"
}


def is_sensitive_file(filename):
    name = filename.lower()
    extension = os.path.splitext(name)[1]

    return (
        name in SENSITIVE_FILE_NAMES
        or name.startswith(".env.")
        or name.startswith("secrets.")
        or name.startswith("credentials.")
        or extension in SENSITIVE_EXTENSIONS
    )


def _read_text_file(file_path, filename):
    """Read a non-oversized UTF-8 text file, returning None if skipped or unreadable."""
    try:
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            print(f"Skipping large file: {filename}")
            return None
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def _is_documentation_file(filename):
    lower = filename.lower()
    return (
        lower.endswith((".md", ".txt", ".rst"))
        or lower in {"readme", "license", "changelog"}
    )


def _walk_repository_files(repo_path, include_code=True, include_docs=True):
    """Walk repository once and extract code and/or documentation documents."""
    code_docs = []
    doc_docs = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRS]

        for file in files:
            if is_sensitive_file(file):
                print(f"Skipping sensitive file: {file}")
                continue

            extension = os.path.splitext(file)[1].lower()
            is_code = include_code and extension in CODE_EXTENSIONS
            is_doc = include_docs and _is_documentation_file(file)

            if not (is_code or is_doc):
                continue

            file_path = os.path.join(root, file)
            content = _read_text_file(file_path, file)
            if content is None:
                continue

            if is_code:
                code_docs.append({
                    "type": "code",
                    "file": file,
                    "path": file_path,
                    "content": content,
                })
            if is_doc:
                doc_docs.append({
                    "type": "documentation",
                    "file": file,
                    "path": file_path,
                    "content": content,
                })

    return code_docs, doc_docs


def extract_code(repo_path):
    """
    Extract source code files from the repository.
    """
    code_docs, _ = _walk_repository_files(repo_path, include_code=True, include_docs=False)
    return code_docs


def extract_documentation(repo_path):
    """
    Extract README and Markdown documentation.
    """
    _, doc_docs = _walk_repository_files(repo_path, include_code=False, include_docs=True)
    return doc_docs


def extract_git_history(repo_path):
    """
    Extract Git commit history.
    """

    documents = []
    repo = None

    try:
        repo = Repo(repo_path)

        for commit in repo.iter_commits(max_count=100):

            commit_text = f"""
Commit Hash: {commit.hexsha}

Author: {commit.author.name}

Date: {commit.committed_datetime}

Commit Message:
{commit.message}
"""

            documents.append({
                "type": "git_history",
                "file": "git_history",
                "path": repo_path,
                "content": commit_text
            })

    except Exception as e:

        print("Could not read Git history:", e)

    finally:
        if repo is not None:
            try:
                repo.close()
            except Exception:
                pass

    return documents


def load_repository(repo_path):

    code, documentation = _walk_repository_files(repo_path, include_code=True, include_docs=True)

    git_history = extract_git_history(repo_path)

    documents = code + documentation + git_history

    return documents


if __name__ == "__main__":

    repo_path = "repo"

    documents = load_repository(repo_path)

    print("\nRepository Analysis")
    print("-------------------")

    print("Total documents:", len(documents))

    code_count = sum(
        1 for doc in documents
        if doc["type"] == "code"
    )

    documentation_count = sum(
        1 for doc in documents
        if doc["type"] == "documentation"
    )

    git_count = sum(
        1 for doc in documents
        if doc["type"] == "git_history"
    )

    print("Code files:", code_count)
    print("Documentation files:", documentation_count)
    print("Git commits:", git_count)