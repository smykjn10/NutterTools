
import uvicorn
from fastapi import FastAPI, Query
from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session, select
from database import db
from api.assets import router

async def lifespan(app:FastAPI):
    #----Start Up Logic
    print("initializing database")
    await db.init_db()
    #----Shut down logic
    yield




app = FastAPI(lifespan=lifespan)



app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app)