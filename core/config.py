from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GROWW_API_KEY: str
    GROWW_SECRET: str
    PAPER_TRADING_MODE: bool = True
    SQUEEZE_THRESHOLD: float = 0.05
    HIGH_VOL_THRESHOLD: float = 1.1
    BULLISH_RSI: float =58
    BEARISH_RSI:float= 40
    LOOK_BACK_PD:int = 60  # Daily time frame for support and resistance

    # Pydantic ko batao ki .env file kahan hai
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
