"""
Migration API with FastAPI
Provides REST endpoints and WebSocket support for migration management.

Requirements:
pip install fastapi uvicorn websockets python-multipart pydantic
"""


# ============================================================================
# Run Server
# ============================================================================

# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(
#         "migration_api:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,  # Set to False in production
#         log_level="info"
#     )
