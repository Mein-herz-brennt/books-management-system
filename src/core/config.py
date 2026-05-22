from decouple import config, Csv
from pydantic import BaseModel, SecretStr, Field

class JWTConfig(BaseModel):
    ACCESS_SECRET_KEY: SecretStr = SecretStr(config('ACCESS_SECRET_KEY', default='dev_access_secret_key_change_me_in_production'))
    REFRESH_SECRET_KEY: SecretStr = SecretStr(config('REFRESH_SECRET_KEY', default='dev_refresh_secret_key_change_me_in_production'))
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

class Settings:
    host: list[str] = Field(default_factory=lambda: config("HOST", cast=Csv(), default="localhost,127.0.0.1"))
    port: int = config("PORT", cast=int, default=8000)
    DATABASE_URL: str = config('DATABASE_URL', cast=str, default="postgresql+asyncpg://postgres:postgres@localhost:5432/books_db")
    token: JWTConfig = JWTConfig()


settings = Settings()