from decouple import config, Csv
from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings
from typing import Any

class JWTConfig(BaseModel):
    ACCESS_SECRET_KEY: SecretStr = config('ACCESS_SECRET_KEY', default='secret')
    REFRESH_SECRET_KEY: SecretStr = config('REFRESH_SECRET_KEY', default='secret_refresh')
    _ACCESS_TIME_TO_EXPIRE: int = 30  # in minutes
    _REFRESH_TIME_TO_EXPIRE: int = 7  # in days
    _ALGORITHM: str = 'HS256'

    @property
    def access_time_to_expire(self):
        return self._ACCESS_TIME_TO_EXPIRE

    @access_time_to_expire.setter
    def access_time_to_expire(self, value: int):
        """TAKE TIME IN MINUTES"""
        if value:
            self._ACCESS_TIME_TO_EXPIRE = value

    @property
    def refresh_time_to_expire(self):
        return self._REFRESH_TIME_TO_EXPIRE

    @refresh_time_to_expire.setter
    def refresh_time_to_expire(self, value: int):
        """TAKE TIME IN DAYS"""
        if value:
            self._REFRESH_TIME_TO_EXPIRE = value

    @property
    def algorithm(self):
        """Crypto algorythm for coding jwt data \n
            default: HS256"""
        return self._ALGORITHM

    @algorithm.setter
    def algorithm(self, value: str):
        if value:
            self._ALGORITHM = value

class Settings(BaseSettings):
    host: list[str] = config("HOST", cast=Csv, default="localhost,127.0.0.1")
    port: int = config("PORT", cast=int, default=8000)
    DATABASE_URL: str = config('DATABASE_URL', cast=str, default="sqlite+aiosqlite:///books.db")
    token: JWTConfig = JWTConfig()

    @field_validator("host", mode="before")
    @classmethod
    def parse_csv_host(cls, v: Any) -> list[str]:
        if isinstance(v, Csv):
            val_str = str(v.cast)
            return [x.strip() for x in val_str.split(v.delimiter)]
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        return v


settings = Settings()