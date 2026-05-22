import uvicorn

from payment.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "payment.app:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
    )
