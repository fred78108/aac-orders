from shared.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@postgres-orders:5432/orders_db"
    )
    service_port: int = 8001


settings = Settings()
