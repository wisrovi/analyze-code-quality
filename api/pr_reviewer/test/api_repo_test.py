#!/usr/bin/env python3
"""
Test script for /analyze-repo endpoint
Tests the analysis of all Pull Requests in a repository
"""

import requests
import json
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8034"
ENDPOINT = "/analyze-repo"

# Test data
repo_url = "https://github.com/cimacorporate/004-body-part-segmentation"
base_dir = "test_output_repo"


def test_repo_analysis():
    """Test repository analysis endpoint"""

    print(f"🧪 Testing repository analysis...")
    print(f"📋 Repository URL: {repo_url}")
    print(f"📁 Base directory: {base_dir}")
    print("-" * 50)

    # Prepare form data
    form_data = {"repo_url": repo_url, "base_dir": base_dir}

    try:
        # Make POST request with form data
        print("📤 Sending request to API...")
        response = requests.post(
            f"{API_BASE_URL}{ENDPOINT}",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Success! Response received:")
            print(f"   Status: {result.get('status')}")
            print(f"   Repository URL: {result.get('repo_url')}")
            print(f"   Processed PRs: {result.get('processed_count')}")
            print(f"   CSV Path: {result.get('csv_path')}")

            # Check if CSV file was created
            csv_path = result.get("csv_path")
            if csv_path and Path(csv_path).exists():
                print(f"   ✅ CSV file exists at {csv_path}")
                # Show CSV file size
                csv_size = Path(csv_path).stat().st_size
                print(f"   📄 CSV file size: {csv_size} bytes")
            else:
                print(f"   ⚠️  CSV file not found at {csv_path}")

            print("\n🎉 Repository analysis test completed successfully!")
            return True

        else:
            print(f"❌ Error occurred!")
            print(f"   Status Code: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error Detail: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Response Text: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not connect to API")
        print(f"   Make sure to API is running at {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False


def test_health_check():
    """Test health check endpoint"""
    print("\n🏥 Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health check passed: {result.get('status')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_api_info():
    """Test API root endpoint to see available endpoints"""
    print("\n📋 Testing API info...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            result = response.json()
            print("✅ API Info:")
            print(f"   Message: {result.get('message')}")
            print(f"   Version: {result.get('version')}")
            endpoints = result.get("endpoints", {})
            print("   Available endpoints:")
            for endpoint, description in endpoints.items():
                print(f"     {endpoint}: {description}")
            return True
        else:
            print(f"❌ API info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API info error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting API Repository Test")
    print("=" * 50)

    # Test health check first
    health_ok = test_health_check()

    if health_ok:
        # Test API info
        info_ok = test_api_info()

        if info_ok:
            # Test repository analysis
            success = test_repo_analysis()

            if success:
                print("\n🎊 All tests passed!")
                print(f"📁 Check the '{base_dir}' directory for generated files.")
            else:
                print("\n💥 Repository analysis test failed!")
                exit(1)
        else:
            print("\n💥 API info test failed!")
            exit(1)
    else:
        print("\n💥 Health check failed! Cannot proceed with repository analysis test.")
        exit(1)
