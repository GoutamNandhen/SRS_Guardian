"""ASGI entrypoint for the intentionally faulty separate router module."""
from fastapi import FastAPI
from examples.m10.router_buggy import router

app = FastAPI(title="M10 multi-module buggy fixture")
app.include_router(router)
