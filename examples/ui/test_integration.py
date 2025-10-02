#!/usr/bin/env python3
"""Test script for Wine Marketing Analytics Platform integration.

This script tests the marketing adapter in both local and HTTP modes.

Usage:
    python test_integration.py [--mode local|http]
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from services.marketing_adapter import MarketingAdapter


async def test_local_mode():
    """Test adapter in local mode."""
    print("\n" + "="*60)
    print("Testing Local Mode")
    print("="*60)

    # Set environment for local mode
    os.environ["MARKETING_MODE"] = "local"
    os.environ["MARKETING_PLATFORM_PATH"] = "/Users/andreyzherditskiy/work/bc/omt-pai-4"

    try:
        adapter = MarketingAdapter()
        print(f"✓ Adapter initialized in {adapter.mode} mode")

        # Test preset filter
        print("\nTest 1: Preset filter (VIP customers only)")
        result = await adapter.query("VIP customers only", limit=10)

        if result.get("success"):
            print(f"✓ Query successful")
            print(f"  - Count: {result.get('count', 0)}")
            print(f"  - Engine: {result.get('engine_used', 'unknown')}")
            print(f"  - Time: {result.get('execution_time', 0):.2f}s")
            print(f"  - Tokens: {result.get('tokens_used', 0)}")
        else:
            print(f"✗ Query failed: {result.get('error')}")
            return False

        # Test custom query
        print("\nTest 2: Custom query (HORECA segment)")
        result = await adapter.query("Show me HORECA customers", limit=10)

        if result.get("success"):
            print(f"✓ Query successful")
            print(f"  - Count: {result.get('count', 0)}")
            print(f"  - Engine: {result.get('engine_used', 'unknown')}")
            print(f"  - Time: {result.get('execution_time', 0):.2f}s")
        else:
            print(f"✗ Query failed: {result.get('error')}")
            return False

        # Test get_filters
        print("\nTest 3: Get available filters")
        filters = await adapter.get_filters()
        print(f"✓ Found {len(filters)} preset filters:")
        for f in filters[:3]:
            print(f"  - {f}")

        # Test get_summary
        print("\nTest 4: Get customer summary")
        summary = await adapter.get_summary()
        if summary:
            print(f"✓ Summary retrieved:")
            print(f"  - Total customers: {summary.get('total_customers', 0)}")
            print(f"  - Total LTV: ${summary.get('total_lifetime_value', 0):,.2f}")
        else:
            print("✗ Summary failed")
            return False

        await adapter.close()
        print("\n✓ Local mode tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Local mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_http_mode():
    """Test adapter in HTTP mode."""
    print("\n" + "="*60)
    print("Testing HTTP Mode")
    print("="*60)
    print("\nNOTE: This test requires Flask API running at http://localhost:5001")
    print("Start it with: cd /Users/andreyzherditskiy/work/bc/omt-pai-4 && make http")

    # Set environment for HTTP mode
    os.environ["MARKETING_MODE"] = "http"
    os.environ["MARKETING_API_URL"] = "http://localhost:5001"
    os.environ["MARKETING_API_KEY"] = "Rwq6L-pWz3tWAMO_SDjnl9aDYZZHjK94NH-lCupeQaw"

    try:
        adapter = MarketingAdapter()
        print(f"✓ Adapter initialized in {adapter.mode} mode")

        # Test health check
        print("\nTest 1: Health check")
        try:
            response = await adapter.http_client.get("/health")
            if response.status_code == 200:
                print(f"✓ Flask API is healthy")
            else:
                print(f"✗ Flask API returned {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Cannot connect to Flask API: {e}")
            print("Make sure Flask API is running!")
            return False

        # Test preset filter
        print("\nTest 2: Preset filter (VIP customers only)")
        result = await adapter.query("VIP customers only", limit=10)

        if result.get("success"):
            print(f"✓ Query successful")
            print(f"  - Count: {result.get('count', 0)}")
            print(f"  - Time: {result.get('execution_time', 0):.2f}s")
        else:
            print(f"✗ Query failed: {result.get('error')}")
            return False

        await adapter.close()
        print("\n✓ HTTP mode tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ HTTP mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run integration tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Test marketing integration")
    parser.add_argument("--mode", choices=["local", "http", "both"], default="both",
                       help="Test mode (default: both)")
    args = parser.parse_args()

    print("Wine Marketing Analytics Platform Integration Test")
    print("="*60)

    success = True

    if args.mode in ["local", "both"]:
        success = await test_local_mode() and success

    if args.mode in ["http", "both"]:
        success = await test_http_mode() and success

    print("\n" + "="*60)
    if success:
        print("✓ All tests passed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Start the UI: cd /Users/andreyzherditskiy/work/panda-agi/examples/ui && ./start.sh")
        print("2. Open browser: http://localhost:3000")
        print("3. Try queries like 'VIP customers only' or 'Show HORECA segment'")
    else:
        print("✗ Some tests failed!")
        print("="*60)
        print("\nTroubleshooting:")
        print("1. Check environment variables in .env file")
        print("2. Ensure omt-pai-4 project exists at correct path")
        print("3. Verify OpenAI API key is set")
        print("4. For HTTP mode, start Flask API first")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
