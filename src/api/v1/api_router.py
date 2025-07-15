from fastapi import APIRouter

from src.api.v1.routers import input, scrape

# Define the main API router for this version (v1)
api_v1_router = APIRouter()

# Include the router from the chat file
api_v1_router.include_router(input.router)
api_v1_router.include_router(scrape.router)
