from sqlmodel import SQLModel, Field, String
from typing import Literal
from datetime import datetime, timezone


class Trade(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None, )
    asset_id: int = Field(foreign_key="asset_master.id")
    entry_time: datetime = Field(default=None)
    entry_price: float = Field(gt=0)
    position_size: int = Field(gt=0)
    exit_time: datetime = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) #imp
    modified_at: datetime | None = Field(default=None)
    status: Literal["OPEN", "CLOSED"] = Field(sa_type=String)
    realized_pnl: float | None = Field(default=None)
