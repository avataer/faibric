"""
GitHub Sync Service for pulling code changes from repositories.

This service enables syncing project code with GitHub repositories,
allowing updates to App.jsx and other frontend code to be pulled
from version-controlled sources.
"""

import base64
import logging
import requests

logger = logging.getLogger(__name__)


class GitHubSyncService:
    """
    Service for synchronizing project code with GitHub repositories.

    Handles fetching commits, file contents, and updating project
    frontend_code from the repository.
    """

    def __init__(self, github_token, repo_owner, repo_name):
        """
        Initialize the GitHub sync service.

        Args:
            github_token: Personal access token for GitHub API
            repo_owner: Owner of the repository (user or org)
            repo_name: Name of the repository
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        logger.info(
            "[INIT] GitHubSyncService configured for %s/%s",
            repo_owner, repo_name
        )

    def get_latest_commit(self, branch="main"):
        """
        Fetch the latest commit SHA for a branch.

        Args:
            branch: Branch name to get the latest commit from

        Returns:
            str: The SHA of the latest commit, or None if failed
        """
        url = f"{self.base_url}/commits/{branch}"
        logger.info("[API] Fetching latest commit for branch: %s", branch)

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            commit_data = response.json()
            sha = commit_data.get("sha")
            logger.info("[OK] Latest commit SHA: %s", sha[:8] if sha else "None")
            return sha
        except requests.exceptions.RequestException as e:
            logger.error("[ERROR] Failed to fetch latest commit: %s", str(e))
            return None

    def get_file_content(self, path, ref="main"):
        """
        Get the decoded content of a file from the repository.

        Args:
            path: Path to the file in the repository
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            str: Decoded file content, or None if failed
        """
        url = f"{self.base_url}/contents/{path}"
        params = {"ref": ref}
        logger.info("[API] Fetching file: %s (ref: %s)", path, ref)

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()
            file_data = response.json()

            # GitHub returns content as base64 encoded
            encoded_content = file_data.get("content", "")
            # Remove newlines that GitHub adds to base64 content
            encoded_content = encoded_content.replace("\n", "")
            decoded_content = base64.b64decode(encoded_content).decode("utf-8")

            logger.info(
                "[OK] File fetched successfully (%d bytes)",
                len(decoded_content)
            )
            return decoded_content
        except requests.exceptions.RequestException as e:
            logger.error("[ERROR] Failed to fetch file %s: %s", path, str(e))
            return None
        except (base64.binascii.Error, UnicodeDecodeError) as e:
            logger.error("[ERROR] Failed to decode file content: %s", str(e))
            return None

    def pull_changes(self, project):
        """
        Pull App.jsx content from GitHub and save to project.

        Args:
            project: Project model instance to update

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(
            "[SYNC] Pulling changes for project: %s",
            project.name if hasattr(project, 'name') else str(project)
        )

        # Fetch App.jsx content from the repository
        content = self.get_file_content("src/App.jsx")

        if content is None:
            logger.error("[ERROR] Failed to pull App.jsx content")
            return False

        # Update project frontend_code
        project.frontend_code = content
        project.save(update_fields=["frontend_code", "updated_at"])

        logger.info(
            "[OK] Project frontend_code updated (%d bytes)",
            len(content)
        )
        return True

    def check_for_updates(self, project):
        """
        Check if the repository has updates compared to stored SHA.

        Args:
            project: Project model instance with optional current_sha attribute

        Returns:
            dict: Status information with keys:
                - has_updates: bool indicating if updates available
                - current_sha: SHA stored on project (or None)
                - latest_sha: Latest SHA from repository (or None)
        """
        logger.info("[CHECK] Checking for updates...")

        current_sha = getattr(project, 'current_sha', None)
        latest_sha = self.get_latest_commit()

        has_updates = (
            latest_sha is not None
            and current_sha != latest_sha
        )

        result = {
            "has_updates": has_updates,
            "current_sha": current_sha,
            "latest_sha": latest_sha
        }

        if has_updates:
            logger.info(
                "[UPDATE] Updates available: %s -> %s",
                current_sha[:8] if current_sha else "None",
                latest_sha[:8] if latest_sha else "None"
            )
        else:
            logger.info("[OK] No updates available")

        return result
