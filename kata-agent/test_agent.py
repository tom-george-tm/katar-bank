#!/usr/bin/env python3
"""
Integration Test Script for Vision Agent
=========================================

This script tests the full flow: Test Script -> Client -> Agent

Flow:
1. Verifies environment setup (loads .env)
2. Ensures test file exists in upload/
3. Calls the A2A client to communicate with the agent
4. Validates the agent response

Run this script with:
    python test_agent.py

The agent must be running locally via Docker Compose:
    docker-compose up -d
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Load environment variables from .env
from dotenv import load_dotenv


def load_environment() -> bool:
    """Load environment variables from .env file.
    
    Returns:
        bool: True if .env was found and loaded, False otherwise.
    """
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Environment loaded from {env_path}")
        return True
    else:
        print(f"✗ .env file not found at {env_path}")
        return False


def verify_test_file() -> Optional[str]:
    """Verify that a test file exists in the upload folder.
    
    Returns:
        Optional[str]: Path to the first test file found, or None if no files exist.
    """
    upload_folder = Path(__file__).parent / "upload"
    
    if not upload_folder.exists():
        print(f"✗ Upload folder not found at {upload_folder}")
        return None
    
    files = [f for f in upload_folder.iterdir() if f.is_file()]
    
    if not files:
        print(f"✗ No test files found in {upload_folder}")
        return None
    
    test_file = files[0]
    file_size = test_file.stat().st_size
    print(f"✓ Test file found: {test_file.name} ({file_size} bytes)")
    return str(test_file)


async def verify_agent_connectivity() -> bool:
    """Verify that the agent is accessible at the configured URL.
    
    Uses the same A2ACardResolver as the client for accurate connectivity check.
    
    Returns:
        bool: True if agent is accessible, False otherwise.
    """
    import httpx
    
    base_url = os.getenv("A2A_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    
    try:
        from a2a.client import A2ACardResolver
        
        # A2ACardResolver tries multiple endpoints and retries
        # Use a longer timeout for initial connection
        async with httpx.AsyncClient(timeout=10.0) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
            agent_card = await resolver.get_agent_card()
            
            if agent_card:
                print(f"✓ Agent is accessible at {base_url}")
                print(f"  Agent: {agent_card.name} v{agent_card.version}")
                return True
            else:
                print(f"✗ Cannot retrieve agent card from {base_url}")
                return False
    except asyncio.TimeoutError:
        print(f"✗ Connection timeout to agent at {base_url}")
        print("  Is the agent running? Try: docker-compose up -d")
        return False
    except Exception as e:
        print(f"✗ Cannot connect to agent at {base_url}: {type(e).__name__}: {e}")
        print("  Is the agent running? Try: docker-compose up -d")
        return False


async def run_client_test() -> bool:
    """Run the client integration test.
    
    Returns:
        bool: True if test passed, False otherwise.
    """
    try:
        from client.client import run as client_run
        
        print("\n" + "="*60)
        print("Running Client Integration Test")
        print("="*60)
        
        await client_run()
        
        print("\n" + "="*60)
        print("✓ Test Completed Successfully")
        print("="*60)
        return True
        
    except asyncio.TimeoutError:
        print(f"\n✗ Client test timed out")
        print("  The agent may be overloaded or not responding")
        return False
    except Exception as e:
        print(f"\n✗ Client test failed with error: {type(e).__name__}")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        return False


async def main() -> int:
    """Main test orchestration function.
    
    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    print("\n" + "="*60)
    print("Vision Agent Integration Test Suite")
    print("="*60 + "\n")
    
    # Step 1: Load environment
    print("[1/4] Loading Environment...")
    if not load_environment():
        print("Failed to load environment configuration")
        return 1
    print()
    
    # Step 2: Verify test file
    print("[2/4] Verifying Test File...")
    test_file = verify_test_file()
    if not test_file:
        print("Test file verification failed")
        return 1
    print()
    
    # Step 3: Verify agent connectivity
    print("[3/4] Verifying Agent Connectivity...")
    if not await verify_agent_connectivity():
        print("Agent connectivity check failed. Is the agent running?")
        print("Start the agent with: docker-compose up -d")
        return 1
    print()
    
    # Step 4: Run client integration test
    print("[4/4] Running Client Integration Test...")
    success = await run_client_test()
    
    if success:
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("TEST FAILED ✗")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
