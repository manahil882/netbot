from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, chat, docs
# audio.py is still a stub -- wire it in here once it has a router:
# from app.routers import audio

app = FastAPI(title="Netbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(docs.router)
# app.include_router(audio.router)


@app.get("/")
def home():
    return {"message": "Backend Running"}
