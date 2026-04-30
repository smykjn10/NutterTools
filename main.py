
import uvicorn
from fastapi import FastAPI, Query
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select
from database import db
from api.assets import router
from service_layer import ScreenerService

async def lifespan(app:FastAPI):
    #----Start Up Logic
    print("initializing database")
    await db.init_db()
    today_watchlist = ScreenerService()
    #----Shut down logic
    yield




app = FastAPI(lifespan=lifespan)



app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app)