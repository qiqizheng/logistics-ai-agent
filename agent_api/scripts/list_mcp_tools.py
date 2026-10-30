"""List tools exposed by the configured logistics MCP service."""

import asyncio
import os

from mcp import Client


async def main() -> None:
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
    async with Client(server_url) as client:
        result = await client.list_tools()
        for tool in result.tools:
            print(tool.name)


if __name__ == "__main__":
    asyncio.run(main())
