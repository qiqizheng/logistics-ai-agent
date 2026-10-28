"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APIStatusError, APITimeoutError

from logistics_agent_api.agent import AgentService
from logistics_agent_api.config import Settings
from logistics_agent_api.llm import LLMConfigurationError, LLMService
from logistics_agent_api.mcp_client import OrderMCPClient
from logistics_agent_api.memory import MemoryMessage, MemoryStore
from logistics_agent_api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    HealthResponse,
    MessageResponse,
)


logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    llm_service: LLMService | None = None,
    agent_service: AgentService | None = None,
) -> FastAPI:
    config = settings or Settings.from_environment()
    memory = MemoryStore(config.memory_db_path)
    llm = llm_service or LLMService(config)
    agent = agent_service or AgentService(
        llm,
        OrderMCPClient(
            config.mcp_server_url,
            timeout_seconds=config.mcp_timeout_seconds,
        ),
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(memory.initialize)
        application.state.settings = config
        application.state.memory = memory
        application.state.agent = agent
        try:
            yield
        finally:
            await llm.close()

    application = FastAPI(
        title="物流 Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @application.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        conversation_id = payload.conversation_id or str(uuid4())
        user_message = payload.message.strip()
        if not user_message:
            raise HTTPException(status_code=422, detail="message 不能为空")

        history = await run_in_threadpool(
            request.app.state.memory.get_recent_messages,
            conversation_id,
            config.memory_max_messages,
        )
        model_input = [
            *history,
            MemoryMessage(role="user", content=user_message),
        ]

        try:
            agent_answer = await request.app.state.agent.answer(model_input)
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except APITimeoutError as exc:
            raise HTTPException(status_code=504, detail="LLM 请求超时") from exc
        except APIConnectionError as exc:
            raise HTTPException(status_code=502, detail="无法连接 LLM 服务") from exc
        except APIStatusError as exc:
            logger.exception("LLM 服务返回错误状态：%s", exc.status_code)
            raise HTTPException(status_code=502, detail="LLM 服务调用失败") from exc
        except Exception as exc:
            logger.exception("LLM 生成失败")
            raise HTTPException(status_code=502, detail="LLM 生成失败") from exc

        await run_in_threadpool(
            request.app.state.memory.append_exchange,
            conversation_id,
            user_message,
            agent_answer.answer,
        )
        return ChatResponse(
            answer=agent_answer.answer,
            conversation_id=conversation_id,
            tools=agent_answer.tools,
        )

    @application.get(
        "/conversations", response_model=list[ConversationResponse]
    )
    async def list_conversations(request: Request) -> list[ConversationResponse]:
        rows = await run_in_threadpool(
            request.app.state.memory.list_conversations
        )
        return [ConversationResponse(**row) for row in rows]

    @application.get(
        "/conversations/{conversation_id}/messages",
        response_model=list[MessageResponse],
    )
    async def get_messages(
        conversation_id: str, request: Request
    ) -> list[MessageResponse]:
        rows = await run_in_threadpool(
            request.app.state.memory.get_all_messages, conversation_id
        )
        return [MessageResponse(**row) for row in rows]

    @application.delete(
        "/conversations/{conversation_id}", status_code=204
    )
    async def delete_conversation(
        conversation_id: str, request: Request
    ) -> Response:
        deleted = await run_in_threadpool(
            request.app.state.memory.delete_conversation, conversation_id
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="会话不存在")
        return Response(status_code=204)

    return application


app = create_app()
