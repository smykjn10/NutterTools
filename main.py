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
'''
chlo ab analytics engine banate hai aur haan apne framework aur context ko refresh kr lo tum bhool jate ho
 "newly used technical and trading logic ko explain krna", apne response ko technical and trading logics ke 
 pov se critique and review krna, hmare bot ka kaam h bade time frame par hmare lock kiye gye 4 setups k
  according stocks filter krna hmare stock_universe m se each day morning on app start up and then during
   the trading day execution time frame par options buying trades lena call aur put implementing risk management 
   just like a professional trader as of now we are bringing 1d data from yfinance since it has just 4-5 minutes
    latency for it. for execution we will fetch data from broker, as of now we are using GROWW but our app is 
    designed as per strategy pattern and dependency inversion so that we can extend it for others brokers as 
    well. currently we are creating it for single user but have a plan to develop other versions such as v2 
    and so on scaling it for multiple users, we have locked bulk data fetcher, setup today we will focus on
     analytics engine, screener service  and it's api route for requested stock and default universe stock
      implementing sanitization at edge, memorization analysed universe in app.state as we have already discussed
       and developed functionality. we are fixing our pre-developed analytics.py and screener_service since you 
       changed trading logic at the last moment. so please keep all the context alive, use your best knowledge
        related to algo trading, technicality and all. critique and review your response before sharing with me 
        and give reasons as well for each and everything new.
'''
