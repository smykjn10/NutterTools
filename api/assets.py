from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import async_session
from sqlmodel import select
from database import db

router = APIRouter()


@router.get("/symbol")
async def get_assets(symbol: Annotated[str, Query()], session=Depends(db.get_session)):
    return "ok"


@router.get("/rsi/symbol")
async def get_rsi(symbol: Annotated[str, Query()], session=Depends(db.get_session)):
    pass
