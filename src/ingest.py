from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os

print("🚀 Initiating Judicial Knowledge Transfer...")

# 1. PDF Load Karo (Yahan apni BNS PDF ka naam daalna)
pdf_path = "bns_2023.pdf"

if not os.path.exists(pdf_path):
    print(f"❌ Error: '{pdf_path}' file nahi mili! Pehle PDF ko folder mein rakho.")
    exit()

loader = PyPDFLoader(pdf_path)
docs = loader.load()
print(f"📚 PDF Loaded: {len(docs)} pages found.")

# 2. Text ko chote Chunks mein todo (Taaki AI easily samajh sake)
print("✂️ Splitting legal documents into logical chunks...")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(docs)

# 3. Vector Embeddings banakar ChromaDB mein save karo
print("🧠 Creating AI Embeddings & Saving to Local Vault...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Ye directly 'src/vectorstore' folder banayega aur data wahan persist kar dega
vector_db = Chroma.from_documents(
    documents=chunks, 
    embedding=embeddings, 
    persist_directory="src/vectorstore",
    collection_name="judicial_vault"
)

print("✅ BNS 2023 Data Ingested Successfully! Neural Network is now fully armed and ready.")