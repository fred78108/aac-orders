from shared.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@postgres-shipping:5432/shipping_db"
    )
    service_port: int = 8005


settings = Settings()
