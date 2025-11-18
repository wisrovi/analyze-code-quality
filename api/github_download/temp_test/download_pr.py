#!/usr/bin/env python3
import requests
import zipfile
import os

def download_pr_files(pr_url, output_zip="pr_files.zip"):
    """Download PR files as ZIP and extract them"""
    
    # API endpoint
    api_url = "http://0.0.0.0:8033/api/v1/pr/download-pr-files"
    
    # Make POST request to download ZIP
    print(f"Downloading files from PR: {pr_url}")
    print(f"API endpoint: {api_url}")
    
    try:
        response = requests.post(
            api_url,
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={'pr_url': pr_url}
        )
        
        # Check if request was successful
        if response.status_code == 200:
            # Save ZIP file
            with open(output_zip, 'wb') as f:
                f.write(response.content)
            print(f"✅ ZIP downloaded successfully: {output_zip}")
            print(f"📁 File size: {len(response.content)} bytes")
            
            # Extract ZIP
            print(f"\n📦 Extracting {output_zip}...")
            with zipfile.ZipFile(output_zip, 'r') as zip_ref:
                zip_ref.extractall('.')
                file_list = zip_ref.namelist()
            
            print(f"✅ Extracted {len(file_list)} files:")
            for file in sorted(file_list):
                size = os.path.getsize(file) if os.path.isfile(file) else 0
                print(f"  📄 {file} ({size} bytes)")
            
            # Count Python files specifically
            python_files = [f for f in file_list if f.endswith('.py')]
            print(f"\n🐍 Python files: {len(python_files)}")
            
            return True
            
        else:
            print(f"❌ Error downloading files: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # PR URL to download
    pr_url = "https://github.com/wisrovi/analyze-code-quality/pull/1"
    
    print("🚀 PR Files Downloader")
    print("=" * 50)
    
    success = download_pr_files(pr_url)
    
    if success:
        print("\n🎉 Download and extraction completed successfully!")
    else:
        print("\n💥 Download failed!")