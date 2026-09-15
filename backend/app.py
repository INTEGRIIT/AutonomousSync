# backend/app.py
import collections
import collections.abc
import os
from dotenv import load_dotenv
from fastapi import FastAPI

# =========================================================
# PYTHON COMPAT FIX
# =========================================================
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

# =========================================================
# LOAD ENV
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# =========================================================
# IMPORT ROUTERS
# =========================================================
from backend.api.routes import router as api_router
from backend.api.fileRoutes import router as file_router
from backend.api.trialRoutes import router as trial_router
from backend.api.adminRoutes import router as admin_router
from backend.api.verifyRoutes import router as verify_router
from backend.api.sessionRoutes import router as session_router
from backend.api.sessionRoutes import router as session_router  # 🔥 NEW

# =========================================================
# APP INIT
# =========================================================
app = FastAPI(
    title="Autonomous Sync Engine",
    version="1.0.0",
)

# =========================================================
# REGISTER ROUTERS
# =========================================================
app.include_router(api_router)
app.include_router(file_router)
app.include_router(trial_router)
app.include_router(admin_router)
app.include_router(verify_router)
app.include_router(session_router)
app.include_router(session_router)  # 🔥 NEW
