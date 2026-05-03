from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Query
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select
from database import db
from api.assets import router
from service_layer import ScreenerService, AnalyticsEngine, BulkDataFetcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----Start Up Logic
    print("🚀 [System] Booting up Trading Engine...")
    print("initializing database")
    await db.init_db()
    analytics_engine = AnalyticsEngine()
    bulk_fetcher = BulkDataFetcher()
    screener_svc = ScreenerService(
        bulk_fetcher, analytics_engine
    )

    # Caching service layer
    app.state.analytics_engine = analytics_engine
    app.state.bulk_fetcher = bulk_fetcher
    app.state.screener_svc = screener_svc

    # 🚨 RUN THE INITIAL SCAN ON STARTUP! and Cache it🚨
    app.state.watchlist = await screener_svc.get_daily_watchlist()

    print(f"✅ [System] Startup Scan Complete! base uinverse stocks queued for Bot.")

    yield
    # ----Shut down logic


app = FastAPI(lifespan=lifespan)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app)
