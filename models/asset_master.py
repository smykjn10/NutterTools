from sqlmodel import  SQLModel, Field, String
from typing import Literal
from datetime import datetime,timezone


class AssetMaster(SQLModel,table= True):
    __tablename__ = "asset_master"
    id: int | None = Field(primary_key=True, default=None, )
    symbol: str = Field(min_length=1, max_length=20,unique=True, index=True)
    asset_type: Literal["EQUITY", "INDEX", "COMMODITY"] = Field(default="EQUITY",sa_type=String)
    is_active: bool = Field(default=True)
    # Audit timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))