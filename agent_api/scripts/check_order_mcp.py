"""手动检查订单 MCP 连通性，不调用 LLM。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from mcp import Client


async def check(order_no: str) -> None:
    server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
    async with Client(server_url) as client:
        response = await client.call_tool(
            "get_order_detail", {"order_no": order_no}
        )

    print(
        json.dumps(
            {
                "is_error": response.is_error,
                "structured_content": response.structured_content,
                "content": [
                    getattr(item, "text", "") for item in response.content
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("order_no")
    arguments = parser.parse_args()
    asyncio.run(check(arguments.order_no))

