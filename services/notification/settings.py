from shared.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres-notifications:5432/notifications_db"
    service_port: int = 8006


settings = Settings()
