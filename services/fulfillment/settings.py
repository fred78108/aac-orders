from shared.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres-fulfillment:5432/fulfillment_db"
    service_port: int = 8004


settings = Settings()
