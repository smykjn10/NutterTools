from sqlmodel import SQLModel, Field
from datetime import datetime




class SignalLog(SQLModel, table = True):
    __tablename__ = "signal_log"
    id : int | None = Field(primary_key=True)
    asset_id:int | None = Field(foreign_key="asset_master.id", default=None)
    timestamp: datetime | None = Field(default= None)
    rsi_value:float = Field(default=0,ge=0,le=100)
    volume:int | None = (Field(gt=0))
    signal:str | None = Field(default=None)

