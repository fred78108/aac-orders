import uvicorn

from notification.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "notification.app:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
    )
