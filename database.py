from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker




sqlite_file_name = "database.db"
sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"
con_args = {"check_same_thread":False}


class Database:
    def __init__(self):
        self.engine = create_async_engine(url=sqlite_url,echo=True, connect_args=con_args)

    async  def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def get_session(self):
        async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            yield session


    # def create_db_and_tables(self):
    #     SQLModel.metadata.create_all(self.engine)


db = Database()