from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.ext.asyncio import async_session
from sqlmodel import select
from database import db
from pydantic import BaseModel, field_validator

router = APIRouter()


class ScanRequest(BaseModel):
    stock_universe: Optional[list[str]] = None

    @field_validator('stock_universe')
    @classmethod
    def sanitize_and_validate_universe(cls, v):
        if v is not None:
            if len(v) > 50:
                raise ValueError("Bhai, max 50 stocks allowed!")
            return [stock.strip().upper() for stock in v]
        return v


@router.get("/symbol")
async def get_assets(symbol: Annotated[str, Query()], session=Depends(db.get_session)):
    return "ok"


@router.get("/rsi/symbol")
async def get_rsi(symbol: Annotated[str, Query()], session=Depends(db.get_session)):
    pass


@router.get("screener/scan")
async def scan_market(request: Request, stock_universe: ScanRequest):
    """
       Scans the market.
       If custom_universe is provided, it returns results but DOES NOT touch the bot's state.
       If no universe is provided, it acts as a system refresh and updates the bot's state.
   """
    screener = request.app.state.screener_svc
    # Scenario A: User is playing around with custom stocks
    if stock_universe and stock_universe.stock_universe:
        print(f"👤 [User Request] Scanning custom universe: {stock_universe.stock_universe}")

        custom_results = await screener.get_daily_watchlist(requested_universe=stock_universe.stock_universe)

        # 🚨 DO NOT UPDATE app.state.watchlist HERE 🚨
        return {
            "status": "success",
            "type": "user_inquiry",
            "state_updated": False,
            "message": "Custom scan complete. System state was NOT altered.",
            "total_setups": len(custom_results),
            "data": custom_results
        }

        # Scenario B: System/Admin triggers a full refresh of the master F&O universe
    else:
        print("⚙️ [System Request] Refreshing Master Watchlist...")

        master_results = await screener.get_daily_watchlist()

        # 🚨 UPDATE THE BOT'S STATE HERE 🚨
        request.app.state.watchlist = master_results

        return {
            "status": "success",
            "type": "system_refresh",
            "state_updated": True,
            "message": "Master Watchlist refreshed. Bot state updated.",
            "total_setups": len(master_results),
            "data": master_results
        }


@router.get("/system/state")
async def get_system_state(request: Request):
    """Check what the autonomous system is currently looking at."""
    return {
        "total_active": len(request.app.state.watchlist),
        "active_watchlist": request.app.state.watchlist
    }
