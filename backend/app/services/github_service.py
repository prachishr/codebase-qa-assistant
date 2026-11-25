
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


# Backend-specific workspace directory
WORKSPACE_DIR = Path(__file__).resolve().parents[3] / "workspaces"


def remove_directory(path: Path) -> None:
    """Recursively remove a directory, clearing Windows read-only bits (e.g. .git packs)."""
    if not path.exists():
        return

    def _handle_remove_readonly(func, target_path, _exc):
        os.chmod(target_path, stat.S_IWRITE)
        func(target_path)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_handle_remove_readonly)
    else:
        shutil.rmtree(path, onerror=_handle_remove_readonly)


def validate_github_url(github_url: str) -> str:
    """Validate that the URL points to a GitHub repository."""

    parsed_url = urlparse(github_url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.netloc.lower() != "github.com"
        or not parsed_url.path.strip("/")
    ):
        raise ValueError("Please provide a valid HTTPS GitHub repository URL.")

    if parsed_url.query or parsed_url.fragment:
        raise ValueError("GitHub repository URL must not contain query parameters.")

    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) != 2:
        raise ValueError("Please provide a repository URL in owner/repository format.")

    owner, repository = path_parts

    if repository.endswith(".git"):
        repository = repository[:-4]

    if not owner or not repository:
        raise ValueError("Invalid GitHub repository URL.")

    return f"https://github.com/{owner}/{repository}.git"


def clone_repository(
    github_url: str,
    user_id: int,
    repository_id: int
) -> str:
    """Clone a GitHub repository into a user-specific workspace."""

    clone_url = validate_github_url(github_url)

    destination = (
        WORKSPACE_DIR
        / f"user_{user_id}"
        / f"repository_{repository_id}"
    )

    if destination.exists():
        if (destination / ".git").exists():
            return str(destination)

        raise FileExistsError(
            "Workspace exists but is not a valid Git repository."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                clone_url,
                str(destination)
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=300
        )

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Repository cloning timed out.") from exc

    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            exc.stderr.strip() or "Unable to clone the GitHub repository."
        ) from exc

    return str(destination)
