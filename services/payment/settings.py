from shared.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres-payments:5432/payments_db"
    service_port: int = 8002


settings = Settings()
