"""开发环境启动入口。"""

import uvicorn

from logistics_agent_api.config import Settings


if __name__ == "__main__":
    settings = Settings.from_environment()
    uvicorn.run(
        "logistics_agent_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

