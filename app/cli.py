import uvicorn

from .app_factory import create_app

def cli():
    # app = create_app()
    uvicorn.run(
        "app.app_factory:create_app",
        host="0.0.0.0",
        port=8000,
        factory=True,
        reload=True
    )

