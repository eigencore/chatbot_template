from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str
    
    ACCESS_TOKEN: str
    
    APP_ID: str
    
    RECIPIENT_WAID: str
    
    VERSION: str
    
    PHONE_NUMBER_ID: str
    
    APP_SECRET: str

    VERIFY_TOKEN: str
    
    OPENAI_API_KEY: str
    
    OPENAI_ASSISTANT_ID: str
    
    REDIS_URL: str
    
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    class Config:
        env_file = ".env"

settings = Settings()

