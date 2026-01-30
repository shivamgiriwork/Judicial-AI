from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os

def build_judicial_brain():
    loader = PyPDFDirectoryLoader("src/data")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    
    # Secure Local Embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    Chroma.from_documents(documents=chunks, embedding=embeddings, 
                          persist_directory="src/vectorstore", collection_name="judicial_vault")
    print("✅ Success: Knowledge Base Ready!")

if __name__ == "__main__":
    build_judicial_brain()