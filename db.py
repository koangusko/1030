import os
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


# 讀取與 db.py 同一個資料夾裡的 .env
load_dotenv(Path(__file__).with_name(".env"))


def connection_settings():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "event_platform"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.environ["DB_PASSWORD"],
        "connect_timeout": 5,
        "row_factory": dict_row,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = AsyncConnectionPool(
        conninfo="",
        kwargs=connection_settings(),
        min_size=1,
        max_size=5,
        open=False,
    )

    app.state.pool = pool

    try:
        await pool.open(wait=True, timeout=10)
        print("Connected to event_platform")
        yield
    finally:
        await pool.close()


# 提供給路由的 Depends(getDB) 使用
async def getDB(request: Request):
    async with request.app.state.pool.connection() as conn:
        yield conn