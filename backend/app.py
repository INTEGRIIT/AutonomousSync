# backend/app.py
import collections
import collections.abc
import os
from dotenv import load_dotenv
from fastapi import FastAPI


for name in (
    "Mapping",
    "MutableMapping",
    "Sequence",
    "MutableSequence",
    "Set",
    "MutableSet",
):
    if not hasattr(collections, name):
        setattr(collections, name, getattr(collections.abc, name))
        
if not hasattr(collections, "MutableSet"):
    collections.MutableSet = collections.abc.MutableSet

# LOAD ENV VARIABLES (ABSOLUTE PATH — NO GUESSING)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.api.routes import router as api_router

app = FastAPI(
    title="Autonomous Sync Engine",
    version="1.0.0",
)

app.include_router(api_router)