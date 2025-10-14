"""Extracts information from `.env` file"""

import os

from pydantic_settings import BaseSettings


def return_full_path (filename: str = ".env") -> str:
    absolute_path = os.path.abspath(__file__)
    directory_name = os.path.dirname(absolute_path)
    full_path = os.path.join(directory_name, filename)
    return full_path

class Settings(BaseSettings):
    alpha_api_key: str
    db_name: str
    model_directory: str

    class Config:
        env_file = return_full_path(".env")

settings = Settings()


