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


def extract_code(repo_path):
    """
    Extract source code files from the repository.
    """

    documents = []

    for root, dirs, files in os.walk(repo_path):

        # Ignore unnecessary folders
        dirs[:] = [
            d for d in dirs
            if d not in {
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__"
            }
        ]

        for file in files:

            extension = os.path.splitext(file)[1].lower()

            if extension in CODE_EXTENSIONS:

                file_path = os.path.join(root, file)

                try:
                    with open(
                        file_path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as f:

                        content = f.read()

                    documents.append({
                        "type": "code",
                        "file": file,
                        "path": file_path,
                        "content": content
                    })

                except Exception:
                    pass

    return documents


def extract_documentation(repo_path):
    """
    Extract README and Markdown documentation.
    """

    documents = []

    for root, dirs, files in os.walk(repo_path):

        dirs[:] = [
            d for d in dirs
            if d not in {
                ".git",
                ".venv",
                "venv",
                "node_modules"
            }
        ]

        for file in files:

            if file.lower().endswith((".md", ".txt")):

                file_path = os.path.join(root, file)

                try:
                    with open(
                        file_path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as f:

                        content = f.read()

                    documents.append({
                        "type": "documentation",
                        "file": file,
                        "path": file_path,
                        "content": content
                    })

                except Exception:
                    pass

    return documents


def extract_git_history(repo_path):
    """
    Extract Git commit history.
    """

    documents = []

    try:

        repo = Repo(repo_path)

        for commit in repo.iter_commits():

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

    return documents


def load_repository(repo_path):

    code = extract_code(repo_path)

    documentation = extract_documentation(repo_path)

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