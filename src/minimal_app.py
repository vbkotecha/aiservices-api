"""Minimal FastAPI app for testing container health."""
from fastapi import FastAPI
import os
import sys

app = FastAPI(title="AgentServices Minimal")

@app.get("/health")
async def health():
    return {"status": "OK", "msg": "minimal mode", "cwd": os.getcwd()}
