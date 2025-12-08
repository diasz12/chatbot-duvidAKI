"""
GitHub crawler for extracting repository documentation and code
"""

from github import Github, GithubException
from typing import List, Dict, Any
import base64

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GitHubCrawler:
    """Crawl GitHub repositories for documentation and code"""

    def __init__(self):
        """Initialize GitHub client"""
        if not Config.is_github_configured():
            logger.warning("GitHub not configured")
            self.client = None
            return

        try:
            self.client = Github(Config.GITHUB_TOKEN)
            logger.info("GitHubCrawler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.client = None

    def crawl_repositories(self, repo_names: List[str] = None) -> List[Dict[str, Any]]:
        """
        Crawl multiple repositories

        Args:
            repo_names: List of repository names (format: 'owner/repo')

        Returns:
            List of documents with content and metadata
        """
        if not self.client:
            logger.warning("GitHub client not initialized")
            return []

        if not repo_names:
            repo_names = Config.GITHUB_REPOS

        documents = []

        for repo_name in repo_names:
            try:
                docs = self.crawl_repository(repo_name)
                documents.extend(docs)
            except Exception as e:
                logger.error(f"Error crawling repository {repo_name}: {e}")

        logger.info(f"Crawled {len(documents)} documents from {len(repo_names)} repositories")
        return documents

    def crawl_repository(self, repo_name: str) -> List[Dict[str, Any]]:
        """
        Crawl a single repository

        Args:
            repo_name: Repository name (format: 'owner/repo')

        Returns:
            List of documents
        """
        if not self.client:
            logger.warning("GitHub client not initialized")
            return []

        documents = []

        try:
            repo = self.client.get_repo(repo_name)

            # Get README
            readme = self._get_readme(repo)
            if readme:
                documents.append(readme)

            # Get documentation files
            docs = self._get_documentation_files(repo)
            documents.extend(docs)

            # Get issues and PRs (optional, can be disabled for performance)
            # issues = self._get_issues(repo)
            # documents.extend(issues)

            logger.info(f"Crawled {len(documents)} documents from {repo_name}")

        except GithubException as e:
            logger.error(f"GitHub API error for {repo_name}: {e}")
        except Exception as e:
            logger.error(f"Error crawling repository {repo_name}: {e}")

        return documents

    def _get_readme(self, repo) -> Dict[str, Any]:
        """
        Get repository README

        Args:
            repo: PyGithub Repository object

        Returns:
            Document dictionary or None
        """
        try:
            readme = repo.get_readme()
            content = base64.b64decode(readme.content).decode('utf-8')

            metadata = {
                "repo_name": repo.full_name,
                "file_path": readme.path,
                "url": readme.html_url,
                "type": "readme"
            }

            return {
                "content": content,
                "source": "github",
                "metadata": metadata
            }

        except GithubException:
            logger.warning(f"No README found for {repo.full_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting README: {e}")
            return None

    def _get_documentation_files(self, repo) -> List[Dict[str, Any]]:
        """
        Get documentation files from repository

        Args:
            repo: PyGithub Repository object

        Returns:
            List of documents
        """
        documents = []
        doc_extensions = ['.md', '.rst', '.txt']
        doc_paths = ['docs', 'doc', 'documentation', '.github']

        try:
            # Search common documentation directories
            for path in doc_paths:
                try:
                    contents = repo.get_contents(path)
                    documents.extend(self._process_contents(repo, contents, doc_extensions))
                except GithubException:
                    continue

        except Exception as e:
            logger.error(f"Error getting documentation files: {e}")

        return documents

    def _process_contents(
        self,
        repo,
        contents,
        extensions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Recursively process repository contents

        Args:
            repo: PyGithub Repository object
            contents: Contents from GitHub API
            extensions: File extensions to include

        Returns:
            List of documents
        """
        documents = []

        # Handle single file
        if not isinstance(contents, list):
            contents = [contents]

        for content in contents:
            try:
                # Skip non-files
                if content.type != "file":
                    # Recursively process directories
                    if content.type == "dir":
                        sub_contents = repo.get_contents(content.path)
                        documents.extend(self._process_contents(repo, sub_contents, extensions))
                    continue

                # Check file extension
                if not any(content.name.endswith(ext) for ext in extensions):
                    continue

                # Get file content
                file_content = base64.b64decode(content.content).decode('utf-8')

                metadata = {
                    "repo_name": repo.full_name,
                    "file_path": content.path,
                    "url": content.html_url,
                    "type": "documentation"
                }

                documents.append({
                    "content": file_content,
                    "source": "github",
                    "metadata": metadata
                })

            except Exception as e:
                logger.error(f"Error processing {content.path}: {e}")
                continue

        return documents

    def _get_issues(self, repo, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get repository issues and pull requests

        Args:
            repo: PyGithub Repository object
            limit: Maximum number of issues to fetch

        Returns:
            List of documents
        """
        documents = []

        try:
            issues = repo.get_issues(state='all', sort='updated', direction='desc')

            for i, issue in enumerate(issues):
                if i >= limit:
                    break

                # Combine issue title, body, and comments
                content = f"# {issue.title}\n\n{issue.body or ''}\n\n"

                # Add comments
                for comment in issue.get_comments():
                    content += f"## Comment by {comment.user.login}\n{comment.body}\n\n"

                metadata = {
                    "repo_name": repo.full_name,
                    "issue_number": issue.number,
                    "url": issue.html_url,
                    "type": "issue" if not issue.pull_request else "pull_request",
                    "state": issue.state
                }

                documents.append({
                    "content": content,
                    "source": "github",
                    "metadata": metadata
                })

        except Exception as e:
            logger.error(f"Error getting issues: {e}")

        return documents
