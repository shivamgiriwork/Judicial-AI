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
    print("❌ Error: database.py file missing.")

# --- 🔐 SECURITY SETUP ---
SECRET_KEY = "RETRO_X_SUPER_SECRET_KEY_DO_NOT_SHARE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise HTTPException(status_code=401, detail="Invalid Token")
        return phone
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid Token")

app = FastAPI(title="Judicial AI Pro | Team Retro X")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 100% OFFLINE AI SETUP (ENGLISH ONLY) ---
try:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="src/vectorstore", embedding_function=embeddings, collection_name="judicial_vault")
    # Strictly Local Llama 3 (Runs fastest in English)
    llm = ChatOllama(model="llama3", temperature=0.1) 
    print("✅ Fast Offline AI Core Loaded! (English Mode)")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

class LoginRequest(BaseModel): phone: str; password: str
class SignupRequest(BaseModel): phone: str; password: str; first_name: str; last_name: str; email: str; dob: str; location: str
class ChatRequest(BaseModel): query: str; language: str; pdf_text: str = ""

@app.post("/api/login")
def login(req: LoginRequest):
    user_data = check_login(req.phone, req.password)
    if user_data:
        full_info = get_full_user_details(req.phone)
        fname = full_info[3] if full_info and len(full_info) > 3 else user_data[0]
        lname = full_info[4] if full_info and len(full_info) > 4 else "Agent"
        email = full_info[5] if full_info and len(full_info) > 5 else "user@judicial.ai"
        dob = full_info[6] if full_info and len(full_info) > 6 else "2000-01-01"
        loc = full_info[7] if full_info and len(full_info) > 7 else "India"

        access_token = create_access_token(data={"sub": req.phone})
        return {"status": "success", "user": fname, "lname": lname, "phone": req.phone, "email": email, "dob": dob, "location": loc, "access_token": access_token}
    else:
        raise HTTPException(status_code=401, detail="Invalid Credentials!")

@app.post("/api/signup")
def signup(req: SignupRequest):
    success = register_user(req.phone, req.password, req.first_name, req.last_name, req.email, req.dob, req.location)
    if success: return {"status": "success", "message": "Account created!"}
    else: raise HTTPException(status_code=400, detail="User already exists!")


@app.post("/api/chat")
def process_chat(req: ChatRequest, current_user: str = Depends(verify_token)):
    try:
        q = req.query.lower()
        
        # 🔥 1. THE FAST-TRACK DICTIONARY (English Only)
        responses = {
            "theft": "Under Section 303 of BNS 2023, theft is punishable with imprisonment up to 3 years, or a fine, or both.",
            "murder": "Under Section 103 of BNS 2023, the punishment for murder is either the death penalty or life imprisonment, along with a fine.",
            "kidnap": "Under Section 137 of BNS 2023, kidnapping is punishable with imprisonment for up to 7 years and a fine.",
            "hit and run": "Under Section 106(2) of BNS 2023, hit and run cases attract imprisonment up to 10 years and a fine.",
            "defamation": "Under Section 356 of BNS 2023, defamation is punishable with simple imprisonment up to 2 years, a fine, or community service.",
            "rape": "Under Section 63 of BNS 2023, the punishment for rape is rigorous imprisonment for not less than 10 years, which may extend to life imprisonment, and a fine.",
            "fraud": "Under Section 318 of BNS 2023, cheating and fraud are punishable with imprisonment up to 3 years, or with a fine, or both.",
            "reject": "I am a Judicial AI Assistant. I can only provide information related to the Bharatiya Nyaya Sanhita (BNS) 2023."
        }

        # 🎯 2. INTENT MATCHING (Offline Speed Route)
        # Maintained Hindi keywords just in case someone types in Hinglish, but output will be strictly English.
        intent = None
        if any(w in q for w in ["theft", "steal", "bike", "chori"]): intent = "theft"
        elif any(w in q for w in ["murder", "kill", "assassinate", "murdered"]): intent = "murder"
        elif any(w in q for w in ["kidnap", "abduct"]): intent = "kidnap"
        elif any(w in q for w in ["hit and run", "accident", "flee", "run over"]): intent = "hit and run"
        elif any(w in q for w in ["defamation", "insult", "defame"]): intent = "defamation"
        elif any(w in q for w in ["rape", "assault"]): intent = "rape"
        elif any(w in q for w in ["fraud", "cheating", "scam"]): intent = "fraud"
        elif any(w in q for w in ["company", "register", "recipe", "cricket"]): intent = "reject"

        if intent:
            return {"status": "success", "response": responses[intent]}

        # 🧠 3. THE PURE LOCAL RAG FALLBACK (For Out of Syllabus Queries)
        docs = vector_db.similarity_search(req.query, k=2)
        if docs:
            context = "\n".join([d.page_content for d in docs])
            
            local_prompt = f"""You are a highly professional Judicial AI Expert. 
            Read this BNS 2023 law context carefully: '{context}'.
            Based ONLY on the context, answer the user's query: '{req.query}'.
            CRITICAL RULES:
            - Answer STRICTLY in English.
            - Provide a direct, factual, and professional legal response.
            - Do not include internal thinking notes, brackets, or filler words.
            Response:"""
            
            prompt = ChatPromptTemplate.from_template(local_prompt)
            chain = prompt | llm | StrOutputParser()
            final_output = chain.invoke({"input": ""}).strip()
            return {"status": "success", "response": final_output}
        else:
            return {"status": "success", "response": responses["reject"]}

    except Exception as e:
        return {"status": "error", "response": "Local System Overload. Please try again."}