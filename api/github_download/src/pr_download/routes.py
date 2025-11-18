import os
import tempfile
import zipfile
import requests
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..github_client.client import GitHubClient

router = APIRouter()
github_client = GitHubClient()


class PRDownloadResponse(BaseModel):
    pr_url: str
    files_count: int
    files: List[Dict[str, Any]]
    info_path: str
    zip_path: str


@router.post("/download-pr-files")
async def download_pr_files(pr_url: str = Form(...)):
    """Download all changed files from a PR as a zip file"""
    try:
        # Parse PR URL to extract owner, repo, and PR number
        pr_info = github_client.parse_pr_url(pr_url)
        owner = pr_info["owner"]
        repo = pr_info["repo"]
        pr_number = pr_info["pr_number"]
        
        # Check if repository is public
        is_public = github_client.is_repo_public(owner, repo)
        
        # Get PR details including files
        if is_public:
            # Public repo: get files without token
            pr_details = github_client.get_pr_details(owner, repo, pr_number, use_token=False)
        else:
            # Private repo: use token
            if not github_client.token:
                raise HTTPException(status_code=401, detail="Token required for private repository")
            pr_details = github_client.get_pr_details(owner, repo, pr_number, use_token=True)
        
        # Download files and create download_info.json
        info_path = await create_download_info(pr_details["files"], owner, repo, pr_number, is_public)
        
        # Create zip file with all downloaded files
        zip_path = await create_zip_file(pr_details["files"], owner, repo, pr_number)
        
        # Return zip file directly
        zip_filename = f"{owner}_{repo}_pr_{pr_number}_files.zip"
        
        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type="application/zip"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_download_info(files: List[Dict], owner: str, repo: str, pr_number: int, is_public: bool) -> str:
    """Create download_info.json with file list and download individual files"""
    # Create permanent directory for files
    permanent_dir = "/tmp/pr_downloads"
    os.makedirs(permanent_dir, exist_ok=True)
    
    # Create download_info.json
    download_info = {
        "pr_url": f"https://github.com/{owner}/{repo}/pull/{pr_number}",
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
        "files_count": len(files),
        "files": []
    }
    
    # Download each file individually
    for file_info in files:
        try:
            # Download file content (as bytes)
            # Use contents_url for private repos, raw_url for public
            contents_url = file_info.get("contents_url") if not is_public else None
            content = github_client.get_file_content(
                file_info["raw_url"], 
                use_token=not is_public,
                contents_url=contents_url
            )
            
            # Save individual file
            file_path = os.path.join(permanent_dir, file_info["filename"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Add file info to download_info
            download_info["files"].append({
                "filename": file_info["filename"],
                "status": file_info.get("status", "modified"),
                "additions": file_info.get("additions", 0),
                "deletions": file_info.get("deletions", 0),
                "patch_url": file_info.get("patch_url", ""),
                "downloaded": True,
                "file_path": file_path
            })
            
        except Exception as e:
            # Add error info to download_info
            download_info["files"].append({
                "filename": file_info["filename"],
                "status": file_info.get("status", "modified"),
                "additions": file_info.get("additions", 0),
                "deletions": file_info.get("deletions", 0),
                "patch_url": file_info.get("patch_url", ""),
                "downloaded": False,
                "error": str(e)
            })
    
    # Save download_info.json
    info_filename = f"{owner}_{repo}_pr_{pr_number}_download_info.json"
    info_path = os.path.join(permanent_dir, info_filename)
    
    import json
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(download_info, f, indent=2, ensure_ascii=False)
    
    return info_path


async def create_zip_file(files: List[Dict], owner: str, repo: str, pr_number: int) -> str:
    """Create a zip file with all downloaded files"""
    permanent_dir = "/tmp/pr_downloads"
    zip_filename = f"{owner}_{repo}_pr_{pr_number}_files.zip"
    zip_path = os.path.join(permanent_dir, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add info JSON file
        info_filename = f"{owner}_{repo}_pr_{pr_number}_download_info.json"
        info_path = os.path.join(permanent_dir, info_filename)
        if os.path.exists(info_path):
            zipf.write(info_path, info_filename)
        
        # Add all downloaded files
        for file_info in files:
            file_path = os.path.join(permanent_dir, file_info["filename"])
            if os.path.exists(file_path):
                # Add file with its relative path in zip
                zipf.write(file_path, file_info["filename"])
    
    return zip_path