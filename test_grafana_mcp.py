#!/usr/bin/env python3
"""Test script to discover if Grafana has an MCP server and what protocol it uses."""
import asyncio
import json
import httpx
from compass.config import settings

async def test_grafana_mcp_endpoints():
    """Test various MCP endpoint possibilities on Grafana."""

    print(f"🔍 Testing Grafana MCP server at: {settings.grafana_url}\n")
    print(f"   Using service account token: {settings.grafana_token[:20]}...\n")

    endpoints_to_test = [
        "/api/mcp",      # Tempo-style endpoint
        "/mcp",          # Grafana MCP plugin standard
        "/api/plugins/grafana-mcp-app/mcp",  # Plugin-based MCP
    ]

    headers = {
        "Authorization": f"Bearer {settings.grafana_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for endpoint in endpoints_to_test:
            url = f"{settings.grafana_url}{endpoint}"
            print(f"📡 Testing: {url}")

            # Test 1: Simple JSON-RPC 2.0 initialize (like Tempo)
            print(f"   → Trying JSON-RPC 2.0 initialize...")
            try:
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "compass-test",
                            "version": "0.1.0"
                        }
                    }
                }

                response = await client.post(url, json=init_request)
                print(f"   ✅ HTTP {response.status_code}")

                if response.status_code == 200:
                    print(f"   📋 Response headers:")
                    for header, value in response.headers.items():
                        if "mcp" in header.lower() or "session" in header.lower():
                            print(f"      {header}: {value}")

                    try:
                        result = response.json()
                        print(f"   📄 Response body:")
                        print(json.dumps(result, indent=2)[:500])
                    except:
                        print(f"   📄 Response (not JSON): {response.text[:200]}")
                    print()
                    continue  # Success - try next endpoint

            except Exception as e:
                print(f"   ❌ JSON-RPC 2.0 failed: {e}")

            # Test 2: Simple tool format (current GrafanaMCPClient)
            print(f"   → Trying simple tool format...")
            try:
                simple_request = {
                    "tool": "list_tools",
                    "params": {}
                }

                response = await client.post(url, json=simple_request)
                print(f"   ✅ HTTP {response.status_code}")

                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"   📄 Response:")
                        print(json.dumps(result, indent=2)[:500])
                    except:
                        print(f"   📄 Response (not JSON): {response.text[:200]}")
                    print()
                    continue

            except Exception as e:
                print(f"   ❌ Simple tool format failed: {e}")

            # Test 3: GET request to see if endpoint exists
            print(f"   → Trying GET request...")
            try:
                response = await client.get(url)
                print(f"   ✅ HTTP {response.status_code}")
                if response.status_code < 500:
                    try:
                        result = response.json()
                        print(f"   📄 Response:")
                        print(json.dumps(result, indent=2)[:300])
                    except:
                        print(f"   📄 Response: {response.text[:200]}")
            except Exception as e:
                print(f"   ❌ GET failed: {e}")

            print()

    # Test 4: Check if MCP plugin is installed
    print(f"\n🔌 Checking for installed MCP plugins...")
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(f"{settings.grafana_url}/api/plugins")
            if response.status_code == 200:
                plugins = response.json()
                mcp_plugins = [p for p in plugins if "mcp" in p.get("id", "").lower()
                               or "mcp" in p.get("name", "").lower()]

                if mcp_plugins:
                    print("   ✅ Found MCP-related plugins:")
                    for plugin in mcp_plugins:
                        print(f"      - {plugin.get('name')} ({plugin.get('id')})")
                        print(f"        Enabled: {plugin.get('enabled')}")
                        print(f"        Type: {plugin.get('type')}")
                else:
                    print("   ⚠️  No MCP plugins found")
                    print(f"   📋 Total plugins installed: {len(plugins)}")
            else:
                print(f"   ❌ Failed to list plugins: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error checking plugins: {e}")

    # Test 5: Check Grafana datasources (we know this works)
    print(f"\n📊 Listing available datasources...")
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(f"{settings.grafana_url}/api/datasources")
            if response.status_code == 200:
                datasources = response.json()
                print(f"   ✅ Found {len(datasources)} datasources:")
                for ds in datasources[:5]:  # Show first 5
                    print(f"      - {ds.get('name')} (type: {ds.get('type')}, uid: {ds.get('uid')})")
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_grafana_mcp_endpoints())
