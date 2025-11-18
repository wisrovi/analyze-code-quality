import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    github_token: Optional[str] = None
    github_api_url: str = "https://api.github.com"
    my_github_username: str = ""
    
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()