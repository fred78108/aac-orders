from shared.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@postgres-inventory:5432/inventory_db"
    )
    service_port: int = 8003


settings = Settings()
