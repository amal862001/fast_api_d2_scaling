from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    SOCRATA_API_URL: str
    DB_PASSWORD : str
    DB_USER : str
    DB_HOST : str
    DB_PORT : int
    DB_NAME : str
    
    # configuration for loading from .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
settings = Settings()

print(settings.DATABASE_URL)