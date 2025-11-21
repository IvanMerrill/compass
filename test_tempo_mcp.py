#!/usr/bin/env python3
"""Quick test script to discover Tempo MCP server tools."""
import asyncio
import json
from compass.integrations.mcp.tempo_client import TempoMCPClient
from compass.config import settings

async def main():
    """Test Tempo MCP tool discovery."""
    print(f"🔍 Testing Tempo MCP at: {settings.tempo_mcp_url}\n")

    async with TempoMCPClient(url=settings.tempo_mcp_url) as client:
        print("✅ MCP session initialized")
        print(f"   Session ID: {client._mcp_session_id}\n")

        print("📋 Listing available tools...\n")
        try:
            tools = await client.list_tools()
            print("Server Response:")
            print(json.dumps(tools, indent=2))
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\nLet's try reading the Tempo MCP documentation...")
            print("The Tempo MCP server may use a different protocol format.")

if __name__ == "__main__":
    asyncio.run(main())
