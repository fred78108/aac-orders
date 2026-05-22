from fastapi import FastAPI

from fulfillment.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="fulfillment-service", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
