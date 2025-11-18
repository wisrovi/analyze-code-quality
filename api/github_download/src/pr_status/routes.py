from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ..github_client.client import GitHubClient

router = APIRouter()
github_client = GitHubClient()


class PRStatusResponse(BaseModel):
    pr_url: str
    state: str
    mergeable: bool
    merged: bool
    draft: bool
    additions: int
    deletions: int
    changed_files: int
    comments: int
    reviews: int
    approvals: int
    changes_requested: int
    reviewers: List[Dict[str, Any]]
    status_summary: str


class CommentResponse(BaseModel):
    success: bool
    comment_id: int
    comment_url: str
    html_url: str
    message: str
    image_url: Optional[str] = None


@router.post("/analyze", response_model=PRStatusResponse)
async def analyze_pr_status(pr_url: str = Form(...)) -> PRStatusResponse:
    """Analyze PR status including comments, approvals, and reviews"""
    try:
        # Parse PR URL to extract owner, repo, and PR number
        pr_info = github_client.parse_pr_url(pr_url)
        owner = pr_info["owner"]
        repo = pr_info["repo"]
        pr_number = pr_info["pr_number"]
        
        # Check if repository is public
        is_public = github_client.is_repo_public(owner, repo)
        
        # Get PR details
        pr_details = github_client.get_pr_full_details(owner, repo, pr_number, use_token=not is_public)
        
        # Get reviews
        reviews = github_client.get_pr_reviews(owner, repo, pr_number, use_token=not is_public)
        
        # Get comments
        comments = github_client.get_pr_comments(owner, repo, pr_number, use_token=not is_public)
        
        # Analyze reviews
        approvals = sum(1 for review in reviews if review["state"] == "APPROVED")
        changes_requested = sum(1 for review in reviews if review["state"] == "CHANGES_REQUESTED")
        
        # Get unique reviewers
        reviewers = []
        seen_reviewers = set()
        for review in reviews:
            if review["user"]["login"] not in seen_reviewers:
                reviewers.append({
                    "username": review["user"]["login"],
                    "state": review["state"],
                    "submitted_at": review.get("submitted_at")
                })
                seen_reviewers.add(review["user"]["login"])
        
        # Generate status summary
        status_parts = []
        if pr_details["draft"]:
            status_parts.append("Draft")
        elif pr_details["merged"]:
            status_parts.append("Merged")
        elif pr_details["state"] == "closed":
            status_parts.append("Closed")
        else:
            status_parts.append("Open")
            
        if approvals > 0:
            status_parts.append(f"{approvals} approval{'s' if approvals != 1 else ''}")
        if changes_requested > 0:
            status_parts.append(f"{changes_requested} change request{'s' if changes_requested != 1 else ''}")
        if len(comments) > 0:
            status_parts.append(f"{len(comments)} comment{'s' if len(comments) != 1 else ''}")
            
        status_summary = " | ".join(status_parts) if status_parts else "No activity"
        
        return PRStatusResponse(
            pr_url=pr_url,
            state=pr_details["state"],
            mergeable=pr_details.get("mergeable", False),
            merged=pr_details["merged"],
            draft=pr_details["draft"],
            additions=pr_details["additions"],
            deletions=pr_details["deletions"],
            changed_files=pr_details["changed_files"],
            comments=len(comments),
            reviews=len(reviews),
            approvals=approvals,
            changes_requested=changes_requested,
            reviewers=reviewers,
            status_summary=status_summary
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comment", response_model=CommentResponse)
async def create_pr_comment(
    pr_url: str = Form(...),
    comment: str = Form(...),
    image: Optional[UploadFile] = File(None)
) -> CommentResponse:
    """Create a comment on a PR with optional image attachment"""
    try:
        # Parse PR URL to extract owner, repo, and PR number
        pr_info = github_client.parse_pr_url(pr_url)
        owner = pr_info["owner"]
        repo = pr_info["repo"]
        pr_number = pr_info["pr_number"]
        
        # Check if repository is public
        is_public = github_client.is_repo_public(owner, repo)
        
        # For creating comments, we always need a token (even for public repos)
        use_token = True
        if not github_client.token:
            raise HTTPException(
                status_code=401, 
                detail="GitHub token required for creating comments. Please set GITHUB_TOKEN in your environment."
            )
        
        # Handle image upload if provided
        image_url = None
        if image and image.filename:
            # Read image data
            image_data = await image.read()
            
            # Upload image to GitHub
            try:
                image_url = github_client.upload_image_to_github(
                    owner, repo, image_data, image.filename, use_token
                )
                
                # Add image to comment body
                comment_with_image = f"{comment}\n\n![{image.filename}]({image_url})"
            except Exception as e:
                # If image upload fails, continue with text-only comment
                comment_with_image = comment
                image_url = None
        else:
            comment_with_image = comment
        
        # Create the comment
        comment_data = github_client.create_pr_comment(
            owner, repo, pr_number, comment_with_image, use_token
        )
        
        return CommentResponse(
            success=True,
            comment_id=comment_data["id"],
            comment_url=comment_data["url"],
            html_url=comment_data["html_url"],
            message="Comment created successfully",
            image_url=image_url
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))