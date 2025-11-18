#!/usr/bin/env python3
"""
Test script for /open-prs endpoint
Tests fetching open pull requests from a repository
"""

import requests
import json
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8034"
ENDPOINT = "/open-prs"

# Test data
repo_url = "https://github.com/cimacorporate/004-body-part-segmentation"


def test_open_prs():
    """Test open PRs endpoint"""

    print(f"🧪 Testing open PRs endpoint...")
    print(f"📋 Repository URL: {repo_url}")
    print("-" * 50)

    # Prepare form data
    form_data = {"repo_url": repo_url}

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
            print(f"   Open PRs found: {len(result.get('open_prs', []))}")

            # Show details of each PR
            open_prs = result.get("open_prs", [])
            if open_prs:
                print("\n📋 Open Pull Requests:")
                for i, pr in enumerate(open_prs, 1):
                    print(
                        f"   {i}. PR #{pr.get('number', 'N/A')}: {pr.get('title', 'No title')}"
                    )
                    print(f"      URL: {pr.get('url', 'No URL')}")
                    print(f"      Author: {pr.get('author', 'Unknown')}")
                    print(f"      Created: {pr.get('created_at', 'Unknown')}")
                    print(f"      State: {pr.get('state', 'Unknown')}")
                    print(f"      Draft: {pr.get('draft', 'Unknown')}")
                    print()
            else:
                print("   No open PRs found (excluding drafts)")

            print("\n🎉 Open PRs test completed successfully!")
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
        print(f"   Make sure API is running at {API_BASE_URL}")
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
    print("🚀 Starting API Open PRs Test")
    print("=" * 50)

    # Test health check first
    health_ok = test_health_check()

    if health_ok:
        # Test API info
        info_ok = test_api_info()

        if info_ok:
            # Test open PRs endpoint
            success = test_open_prs()

            if success:
                print("\n🎊 All tests passed!")
                print(
                    f"📁 The API successfully retrieved open PRs from the repository."
                )
            else:
                print("\n💥 Open PRs test failed!")
                exit(1)
        else:
            print("\n💥 API info test failed!")
            exit(1)
    else:
        print("\n💥 Health check failed! Cannot proceed with open PRs test.")
        exit(1)
