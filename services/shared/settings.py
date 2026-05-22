from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/db"
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    redis_url: str = "redis://localhost:6379/0"
    debug: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}
