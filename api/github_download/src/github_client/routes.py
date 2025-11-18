from fastapi import APIRouter, HTTPException, Form
from typing import Dict, Any, List
from .client import GitHubClient

router = APIRouter()
github_client = GitHubClient()


@router.post("/repos/pr-urls")
async def get_repo_pr_urls(repo_url: str = Form(...)) -> Dict[str, Any]:
    """Get URLs of all open pull requests for a repository"""
    try:
        pr_urls = github_client.get_open_pull_requests_urls(repo_url)
        return {
            "repo_url": repo_url,
            "pr_count": len(pr_urls),
            "pr_urls": pr_urls
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))