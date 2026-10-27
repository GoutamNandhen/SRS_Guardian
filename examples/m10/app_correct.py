"""ASGI entrypoint: the actual POST handler is defined in another module."""
from fastapi import FastAPI
from examples.m10.router_correct import router

app = FastAPI(title="M10 multi-module correct fixture")
app.include_router(router)
