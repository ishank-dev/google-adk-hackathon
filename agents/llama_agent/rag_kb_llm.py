# imports

import os
import glob
from dotenv import load_dotenv
import gradio as gr
import traceback, sys

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from pathlib import Path
import numpy as np

# Load environment variables
load_dotenv()

# Use vector database at project root level
BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_name = str(BASE_DIR / "vector_db_llama")
DOC_DIR = BASE_DIR / "knowledge-base-slack"

# Global variables for lazy loading
_vectorstore = None
_conversation_chain = None
_llm = None

def get_folders():
    """Get document folders - cached"""
    folders = [p for p in DOC_DIR.iterdir() if p.is_dir()]
    if not folders:
        raise FileNotFoundError(
            f"No Markdown folders found under {DOC_DIR}. "
            "Check the path or ensure knowledge-base-slack exists at root level."
        )
    return folders

def add_metadata(doc, doc_type):
    """Add document type metadata to a document"""
    doc.metadata["doc_type"] = doc_type
    return doc

def load_documents_and_create_vectorstore():
    """Load documents and create/load vector store - ONLY when needed"""
    print("📚 Loading documents...")
    text_loader_kwargs = {'encoding': 'utf-8'}
    folders = get_folders()

    documents = []
    for folder in folders:
        doc_type = os.path.basename(folder)
        loader = DirectoryLoader(folder, glob="**/*.md", loader_cls=TextLoader, loader_kwargs=text_loader_kwargs)
        folder_docs = loader.load()
        documents.extend([add_metadata(doc, doc_type) for doc in folder_docs])

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)

    print(f"✅ Loaded {len(documents)} documents, split into {len(chunks)} chunks")
    return documents, chunks

def get_vectorstore():
    """Lazy load vectorstore - only create when first needed"""
    global _vectorstore
    
    if _vectorstore is not None:
        return _vectorstore
    
    print(f"🔍 Initializing vector database: {db_name}")
    
    # Initialize embeddings
    from langchain_community.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # PERFORMANCE OPTIMIZATION: Check if database exists and is valid
    if os.path.exists(db_name):
        print("⚡ Found existing vector database - loading from cache...")
        try:
            _vectorstore = Chroma(persist_directory=db_name, embedding_function=embeddings)
            count = _vectorstore._collection.count()
            
            if count > 0:
                print(f"✅ Loaded cached vectors: {count} documents ready")
                return _vectorstore
            else:
                print("⚠️ Vector database is empty - rebuilding...")
        except Exception as e:
            print(f"⚠️ Vector database corrupted ({e}) - rebuilding...")
    
    # Create new database
    print("🔄 Creating vector embeddings (30-60 seconds first time)...")
    documents, chunks = load_documents_and_create_vectorstore()
    _vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=db_name)
    print(f"✅ Vector database ready: {_vectorstore._collection.count()} documents")
    
    return _vectorstore

def get_llm():
    """Lazy load LLM - only create when first needed"""
    global _llm
    
    if _llm is not None:
        return _llm
        
    print("🦙 Initializing Llama model...")
    _llm = ChatOpenAI(
        temperature=0.7, 
        model='llama3.2',  # Fixed: use 'model' not 'model_name'
        base_url='http://localhost:11434/v1', 
        api_key='ollama',
        max_tokens=2000  # Add token limit for faster responses
    )
    print("✅ Llama model ready")
    return _llm

def get_conversation_chain():
    """Lazy load conversation chain - only create when first needed"""
    global _conversation_chain
    
    if _conversation_chain is not None:
        return _conversation_chain
    
    print("🔗 Setting up conversation chain...")
    
    vectorstore = get_vectorstore()
    llm = get_llm()
    
    # Enhanced memory configuration
    memory = ConversationBufferMemory(
        memory_key='chat_history', 
        return_messages=True,
        output_key='answer'
    )
    
    # Create retriever with fewer documents for faster processing
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # Reduced from 5 to 3
    
    # Enhanced conversation chain
    _conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm, 
        retriever=retriever, 
        memory=memory,
        return_source_documents=True,
        verbose=True
    )
    
    print("✅ Conversation chain ready")
    return _conversation_chain


def chat(question: str, history=None):
    """Optimized chat function with faster response"""
    if history is None:
        history = []
    
    # Get conversation chain (lazy loaded)
    conversation_chain = get_conversation_chain()
    
    print(f"🤔 Processing question: {question[:50]}...")
    
    try:
        result = conversation_chain.invoke(
            {"question": question, "chat_history": history}
        )
        
        # Format response with source information
        answer = result["answer"]
        source_docs = result.get("source_documents", [])
        
        if source_docs:
            sources = []
            for doc in source_docs[:3]:  # Show top 3 sources
                doc_type = doc.metadata.get('doc_type', 'Unknown')
                source = doc.metadata.get('source', 'Unknown source')
                filename = os.path.basename(source) if source != 'Unknown source' else 'Unknown'
                sources.append(f"• {doc_type}: {filename}")
            
            answer += f"\n\n**Sources consulted:**\n" + "\n".join(sources)
        
        print("✅ Response generated")
        return answer
        
    except Exception as e:
        print(f"❌ Error in chat: {e}")
        return f"Sorry, I encountered an error: {str(e)}"

# Performance monitoring helper
def get_stats():
    """Get performance statistics"""
    if _vectorstore:
        count = _vectorstore._collection.count()
        return f"📊 Vector DB: {count} docs | Status: Ready"
    else:
        return "📊 Vector DB: Not loaded | Status: Lazy loading enabled"