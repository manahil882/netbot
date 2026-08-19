from fastapi import FastAPI, Depends, Header, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy import func
import bcrypt
import jose.jwt as jwt
import os
import shutil


from typing import List
from datetime import datetime,timedelta

from app.schemas import ChatMessageRequest, ChatMessageResponse, ChatMessageCreate
from app.database.models import Message
from app.services.ai_service import generate_reply


# This tells FastAPI to look for an "authorization" header in Swagger
header_scheme = APIKeyHeader(name="authorization", auto_error=False)

SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"

# --- MINIMAL BCRYPT UTILITIES (Replacing pwd_context) ---
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
# --------------------------------------------------------

def get_current_user(token: str = Depends(header_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header"
        )
    
    try:
        # If the token contains "Bearer ", strip it off cleanly
        print("RAW TOKEN:", token)

        if token.lower().startswith("bearer "):
            token = token.split(" ")[1]
        print("TOKEN AFTER STRIP:", token)

        # Decode the real cryptographic payload data
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        print("PAYLOAD:", payload)

        return payload
        
    except Exception as e:
        print("JWT ERROR:" , e)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials / Invalid Token"
        )

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str


class PDFResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    size: str
    status: str
    owner_id: int
    uploaded_at: datetime


    class Config:
        from_attributes = True

def get_db():
    db = SessionalLocal()
    try:
        yield db
    finally:
        db.close()


UPLOAD_DIR = "../uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Backend Running"}


@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = hash_password(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": f"Welcome {new_user.name} created successfully",
        "user_id": new_user.id
    }


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        return {"error": "Invalid credentials"}
    
    if not verify_password(user.password, db_user.password):
        return {"error": "Invalid credentials"}
    
    token = create_access_token(
        data={"user_id": db_user.id, "email": db_user.email}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size_mb = round(file.size / (1024*1024), 1)
    new_pdf = PDF(
        filename=file.filename,
        filepath=file_path,
        size= f"{size_mb} MB",
        pages = 0,   
        subject = "General", 
        status = "ready",
        owner_id=user["user_id"]
    )

    db.add(new_pdf)
    db.commit()
    db.refresh(new_pdf)

    return {
        "message": "PDF uploaded successfully",
        "pdf_id": new_pdf.id,
        "filename": new_pdf.filename
    }


@app.get("/my-pdfs", response_model = List[PDFResponse])
async def get_my_pdfs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
        pdfs = db.query(PDF).filter(PDF.owner_id == current_user["user_id"]).all()
        return pdfs



@app.get("/protected")
def protected_route(user=Depends(get_current_user)):
    return {
        "message": "You are authenticated!",
        "user": user
    }


@app.post("/chat/create")
def create_chat(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = ChatSession(
        user_id=current_user["user_id"]
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return {
        "chat_id": chat.id
    }

@app.get("/my-chats")
def get_my_chats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chats = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id ==
            current_user["user_id"]
        )
        .all()
    )

    return chats



@app.get("/chat/{chat_id}")
def get_chat_messages(
    chat_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return(
        db.query(Message)
        .filter(
            Message.chat_id == chat_id,
            Message.user_id == current_user["user_id"]
        )
        .order_by(Message.created_at)
        .all()
    )


@app.post("/chat/message")
def send_message(
    message: ChatMessageCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):

    # Save user's message
    user_message = Message(
        user_id=user["user_id"],
        chat_id=message.chat_id,
        role="user",
        content=message.content,
    )

    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Generate AI reply
    ai_reply = generate_reply(message.content)

    # Save AI message
    assistant_message = Message(
        user_id=user["user_id"],
        chat_id=message.chat_id,
        role="assistant",
        content=ai_reply,
    )

    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return {
        "reply": assistant_message.content
    }