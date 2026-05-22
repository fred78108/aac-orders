import uvicorn

from shipping.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "shipping.app:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
    )
