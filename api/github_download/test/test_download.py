import requests
import os
import zipfile

def test_download_pr_files():
    """Test downloading PR files from GitHub"""
    
    # API endpoint
    url = "http://localhost:8033/api/v1/pr/download-pr-files"

    # PR URL to test
    pr_url = "https://github.com/cimacorporate/004-body-part-segmentation/pull/64/"

    # Create test directory structure
    test_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(test_dir, "pr_64_extracted")
    zip_file_path = os.path.join(test_dir, "test_pr_64_download.zip")
    
    # Create extraction directory
    os.makedirs(output_dir, exist_ok=True)

    # Make request
    response = requests.post(
        url,
        data={"pr_url": pr_url}
    )
    
    # Check response
    if response.status_code == 200:
        # Save the zip file
        with open(zip_file_path, "wb") as f:
            f.write(response.content)
        print(f"✓ Success! Downloaded {len(response.content)} bytes")
        print(f"✓ File saved as: {zip_file_path}")
        
        # Extract the zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print(f"✓ Extracted to: {output_dir}")
        
        # List extracted files
        print("\nExtracted files:")
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                rel_path = os.path.relpath(file_path, output_dir)
                print(f"  - {rel_path} ({file_size} bytes)")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")

if __name__ == "__main__":
    test_download_pr_files()
