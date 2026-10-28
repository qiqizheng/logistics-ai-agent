"""MySQL 连接配置与连接创建。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.connections import Connection


PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        """从环境变量加载数据库配置。"""
        return cls(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "wq"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            charset=os.getenv("DB_CHARSET", "utf8mb4"),
        )


def create_connection(settings: DatabaseSettings | None = None) -> Connection:
    """创建一个短生命周期的只读查询连接。"""
    config = settings or DatabaseSettings.from_environment()
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset=config.charset,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
    )

