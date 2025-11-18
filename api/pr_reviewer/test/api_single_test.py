#!/usr/bin/env python3
"""
Test script for /analyze-pr endpoint
Tests the analysis of a single Pull Request
"""

import requests
import json
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8034"
ENDPOINT = "/analyze-pr"

# Test data
pr_url = "https://github.com/cimacorporate/004-body-part-segmentation/pull/64"
base_dir = "test_output_single"


def test_single_pr_analysis():
    """Test the single PR analysis endpoint"""

    print(f"🧪 Testing single PR analysis...")
    print(f"📋 PR URL: {pr_url}")
    print(f"📁 Base directory: {base_dir}")
    print("-" * 50)

    # Prepare form data
    form_data = {"pr_url": pr_url, "base_dir": base_dir}

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
            print(f"   PR Number: {result.get('pr_number')}")
            print(f"   Company: {result.get('empresa')}")
            print(f"   Project: {result.get('proyecto')}")
            print(f"   Eligible for merge: {result.get('eligible')}")
            print(f"   PR Directory: {result.get('pr_dir')}")

            # Check if quality report exists
            quality_report = result.get("quality_report", {})
            if quality_report:
                print(f"   Quality Report Keys: {list(quality_report.keys())}")

            print("\n🎉 Single PR analysis test completed successfully!")
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
        print("❌ Connection Error: Could not connect to the API")
        print(f"   Make sure the API is running at {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False


def test_health_check():
    """Test the health check endpoint"""
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


if __name__ == "__main__":
    print("🚀 Starting API Single PR Test")
    print("=" * 50)

    # Test health check first
    health_ok = test_health_check()

    if health_ok:
        # Test single PR analysis
        success = test_single_pr_analysis()

        if success:
            print("\n🎊 All tests passed!")
        else:
            print("\n💥 Test failed!")
            exit(1)
    else:
        print("\n💥 Health check failed! Cannot proceed with PR analysis test.")
        exit(1)
