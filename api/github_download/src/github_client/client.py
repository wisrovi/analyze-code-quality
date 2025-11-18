import requests
import re
import base64
import mimetypes
from typing import Dict, List, Any, Optional
from urllib.parse import unquote
from src.config.settings import settings


class GitHubClient:
    def __init__(self):
        self.token = settings.github_token
        self.base_url = settings.github_api_url

    def _get_headers(self, use_token: bool = True) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if use_token and self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """Parse GitHub URL and extract owner and repo name"""
        # Support both https and ssh URLs
        pattern = r'(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$'
        match = re.match(pattern, repo_url)
        if not match:
            raise ValueError("Invalid GitHub repository URL")
        
        return {
            "owner": match.group(1),
            "repo": match.group(2)
        }

    def is_repo_public(self, owner: str, repo: str) -> bool:
        """Check if repository is public"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = requests.get(url, headers=self._get_headers(use_token=False))
            return response.status_code == 200
        except:
            return False

    def get_open_pull_requests_urls(self, repo_url: str) -> List[str]:
        """Get URLs of all open pull requests for a repository"""
        try:
            repo_info = self.parse_repo_url(repo_url)
            owner = repo_info["owner"]
            repo = repo_info["repo"]
            
            # First check if repository is public
            is_public = self.is_repo_public(owner, repo)
            
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls?state=open"
            
            if is_public:
                # Public repo: access without token
                response = requests.get(url, headers=self._get_headers(use_token=False))
                response.raise_for_status()
                prs = response.json()
                return [pr["html_url"] for pr in prs]
            else:
                # Private repo: use token
                if not self.token:
                    raise Exception("Token required for private repository access")
                
                response = requests.get(url, headers=self._get_headers(use_token=True))
                response.raise_for_status()
                prs = response.json()
                return [pr["html_url"] for pr in prs]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching PRs: {e}")

    def get_pr_details(self, owner: str, repo: str, pr_number: int, use_token: bool = True) -> Dict[str, Any]:
        try:
            headers = self._get_headers(use_token)
            
            files_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
            files_response = requests.get(files_url, headers=headers)
            files_response.raise_for_status()
            files = files_response.json()

            return {
                "files": files
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching details for PR #{pr_number}: {e}")

    def get_file_content(self, raw_url: str, use_token: bool = True, contents_url: Optional[str] = None) -> bytes:
        """
        Get file content from GitHub.
        For private repos, use contents_url with API; for public repos, use raw_url directly.
        """
        try:
            headers = self._get_headers(use_token)
            
            # For private repos with contents_url, use GitHub API
            if use_token and contents_url:
                response = requests.get(contents_url, headers=headers)
                response.raise_for_status()
                content_data = response.json()
                
                # GitHub API returns content as base64
                if 'content' in content_data:
                    import base64
                    return base64.b64decode(content_data['content'])
                else:
                    # Fall back to raw_url
                    decoded_url = unquote(raw_url)
                    response = requests.get(decoded_url, headers=headers)
                    response.raise_for_status()
                    return response.content
            else:
                # For public repos or when no contents_url, use raw_url
                decoded_url = unquote(raw_url)
                response = requests.get(decoded_url, headers=headers)
                response.raise_for_status()
                return response.content
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching file content from {raw_url}: {e}")

    def get_pr_full_details(self, owner: str, repo: str, pr_number: int, use_token: bool = True) -> Dict[str, Any]:
        """Get full PR details including state, mergeability, etc."""
        try:
            headers = self._get_headers(use_token)
            
            pr_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_response = requests.get(pr_url, headers=headers)
            pr_response.raise_for_status()
            pr_data = pr_response.json()

            return {
                "state": pr_data["state"],
                "merged": pr_data["merged"],
                "mergeable": pr_data.get("mergeable"),
                "draft": pr_data["draft"],
                "additions": pr_data["additions"],
                "deletions": pr_data["deletions"],
                "changed_files": pr_data["changed_files"]
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching PR details for #{pr_number}: {e}")

    def get_pr_reviews(self, owner: str, repo: str, pr_number: int, use_token: bool = True) -> List[Dict[str, Any]]:
        """Get all reviews for a PR"""
        try:
            headers = self._get_headers(use_token)
            
            reviews_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
            reviews_response = requests.get(reviews_url, headers=headers)
            reviews_response.raise_for_status()
            return reviews_response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching reviews for PR #{pr_number}: {e}")

    def get_pr_comments(self, owner: str, repo: str, pr_number: int, use_token: bool = True) -> List[Dict[str, Any]]:
        """Get all comments for a PR"""
        try:
            headers = self._get_headers(use_token)
            
            comments_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
            comments_response = requests.get(comments_url, headers=headers)
            comments_response.raise_for_status()
            return comments_response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching comments for PR #{pr_number}: {e}")

    def create_pr_comment(self, owner: str, repo: str, pr_number: int, body: str, use_token: bool = True) -> Dict[str, Any]:
        """Create a comment on a PR"""
        try:
            headers = self._get_headers(use_token)
            
            comments_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
            data = {"body": body}
            
            response = requests.post(comments_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error creating comment on PR #{pr_number}: {e}")

    def upload_image_to_github(self, owner: str, repo: str, image_data: bytes, filename: str, use_token: bool = True) -> str:
        """Upload an image to GitHub releases and return the URL"""
        try:
            if not use_token or not self.token:
                raise Exception("Token required for image upload")
            
            headers = self._get_headers(use_token)
            
            # Determine content type
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            
            # Create a unique name for the image
            import time
            import uuid
            unique_name = f"comment-images/{int(time.time())}_{uuid.uuid4().hex[:8]}_{filename}"
            
            # Upload to GitHub releases (using the repo's releases as a simple image host)
            releases_url = f"{self.base_url}/repos/{owner}/{repo}/releases"
            
            # Check if there's a releases asset we can use, or create a simple release
            release_data = {
                "tag_name": f"comment-images-{int(time.time())}",
                "name": "Comment Images",
                "draft": True,
                "prerelease": True
            }
            
            release_response = requests.post(releases_url, headers=headers, json=release_data)
            release_response.raise_for_status()
            release = release_response.json()
            
            # Upload the image as a release asset
            upload_url = release["upload_url"].replace("{?name,label}", f"?name={unique_name}")
            upload_headers = {
                **headers,
                "Content-Type": content_type
            }
            
            upload_response = requests.post(upload_url, headers=upload_headers, data=image_data)
            upload_response.raise_for_status()
            
            return upload_response.json()["browser_download_url"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error uploading image: {e}")

    def parse_pr_url(self, pr_url: str) -> Dict[str, Any]:
        """Parse PR URL to extract owner, repo, and PR number"""
        import re
        # Support both https and URLs
        pattern = r'(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/]+)/pull/(\d+)(?:/)?$'
        match = re.match(pattern, pr_url)
        if not match:
            raise ValueError("Invalid GitHub PR URL")
        
        return {
            "owner": match.group(1),
            "repo": match.group(2),
            "pr_number": int(match.group(3))
        }