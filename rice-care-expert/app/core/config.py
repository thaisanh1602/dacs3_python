from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Rice Care Expert API"
    VERSION: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()