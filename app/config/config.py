from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    class Config:
        case_sensitive = True

    NAME: str
    DATABASE_HOST: str
    DATABASE_PORT: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    JWT_SECRET_KEY: str


settings = Settings()

from hypercorn.config import Config

config = Config()
config.bind = ["0.0.0.0:443"]
config.certfile = "cert.pem"
config.keyfile = "key.pem"
