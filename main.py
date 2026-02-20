from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from pypdf import PdfReader

# --- AI & LANGCHAIN IMPORTS ---
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- DATABASE IMPORTS ---
try:
    from database import (register_user, check_login, 
                          get_full_user_details, update_user_profile,
                          check_user_exists, reset_password, update_profile_picture)
except ImportError:
    print("❌ Error: database.py file nahi mili ya import mein problem hai.")

# --- 🔐 JWT SECURITY SETUP ---
SECRET_KEY = "RETRO_X_SUPER_SECRET_KEY_DO_NOT_SHARE" # Isko hack karna impossible hai
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # Token 1 ghante mein expire ho jayega

security = HTTPBearer()

def create_access_token(data: dict):
    """User ke liye ek secure JWT token banata hai"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """API hit karne se pehle token check karta hai (The Bouncer)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise HTTPException(status_code=401, detail="Invalid Token Structure")
        return phone
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired! Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Fake or Invalid Token!")

# --- API SETUP ---
app = FastAPI(title="Judicial AI Pro Secure Backend")

# 🌐 STRICT CORS Setup (Ab koi aur website isey use nahi kar sakti)
app.add_middleware(
    CORSMiddleware,
    # Live server defaults to 5500 or 5501. Hum strict allowed origins de rahe hain.
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:5501", "http://localhost:5501"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AI SETUP ---
try:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="src/vectorstore", embedding_function=embeddings, collection_name="judicial_vault")
    llm = ChatOllama(model="llama3", temperature=0.3)
    print("✅ AI Models Securely Loaded!")
except Exception as e:
    print(f"⚠️ AI Setup Warning: {e}")

# --- DATA FORMATS ---
class LoginRequest(BaseModel):
    phone: str
    password: str

class SignupRequest(BaseModel):
    phone: str
    password: str
    first_name: str
    last_name: str
    email: str
    dob: str
    location: str

class ChatRequest(BaseModel):
    query: str
    language: str
    pdf_text: str = ""

# --- 🟢 1. AUTHENTICATION APIs ---

@app.post("/api/login")
def login(req: LoginRequest):
    user_data = check_login(req.phone, req.password)
    if user_data:
        if len(user_data) >= 3:
            name, _, pic_url = user_data[:3]
        else:
            name = user_data[0]
            pic_url = None
            
        # 🎟️ GENERATE VIP TOKEN
        access_token = create_access_token(data={"sub": req.phone})
        
        return {
            "status": "success", 
            "user": name, 
            "phone": req.phone, 
            "pic_url": pic_url,
            "access_token": access_token, # Frontend ko token bhej rahe hain
            "token_type": "bearer"
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid Credentials! Phone ya Password galat hai.")

@app.post("/api/signup")
def signup(req: SignupRequest):
    success = register_user(req.phone, req.password, req.first_name, req.last_name, req.email, req.dob, req.location)
    if success:
        return {"status": "success", "message": "Account successfully create ho gaya! 🎉"}
    else:
        raise HTTPException(status_code=400, detail="User already exists! Is number se account pehle hi bana hai.")

# --- 🧠 2. CHAT & AI API (NOW LOCKED WITH TOKEN) ---

# Notice the 'current_user' dependency. Ye bina valid token ke API run nahi hone dega.
@app.post("/api/chat")
def process_chat(req: ChatRequest, current_user: str = Depends(verify_token)):
    try:
        docs = vector_db.similarity_search(req.query, k=3)
        kb = "\n".join([d.page_content for d in docs])
        
        tpl = f"Act as an expert Indian Lawyer. Language: {req.language}. Strict BNS 2023. Context: {kb}. Document Text: {req.pdf_text}. Question: {req.query}. Provide highly accurate and structured legal advice."
        prompt = ChatPromptTemplate.from_template(tpl)
        
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"input": "dummy"})
        
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")

# --- 📄 3. PDF EXTRACTOR API (LOCKED) ---
@app.post("/api/extract-pdf")
async def extract_pdf(file: UploadFile = File(...), current_user: str = Depends(verify_token)):
    try:
        text = ""
        pdf_reader = PdfReader(file.file)
        for page in pdf_reader.pages:
            text += page.extract_text()
        return {"status": "success", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="PDF read karne mein error aayi.")

@app.get("/")
def read_root():
    return {"message": "Judicial AI  Secure Backend is Online! 🛡️⚡"}