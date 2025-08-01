import os
import glob
import gradio as gr
import pickle
import sys
from huggingface_hub import InferenceClient
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Add debugging
print("🔍 Starting debug version...")
print(f"🔍 Current working directory: {os.getcwd()}")
print(f"🔍 Python version: {sys.version}")

# Configuration
MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
DB_NAME = "vector_db"
EMBEDDINGS_FILE = "hf_embeddings.pkl"

# Get Hugging Face token from environment
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
print(f"🔍 HF_TOKEN available: {bool(HF_TOKEN)}")

# Initialize the Llama client with token
try:
    print("🔍 Initializing InferenceClient...")
    client = InferenceClient(MODEL_NAME, token=HF_TOKEN)
    print(f"✅ InferenceClient initialized successfully")
except Exception as e:
    print(f"❌ Error initializing InferenceClient: {e}")
    client = None

class RAGSystem:
    def __init__(self):
        print("🔍 Initializing RAGSystem...")
        self.embeddings_model = None
        self.vectorstore = None
        self.chunks = []
        self.chunk_embeddings = []
        
    def load_or_create_embeddings(self):
        """Load pre-computed embeddings or create them using OpenAI"""
        print(f"🔍 Checking for embeddings file: {EMBEDDINGS_FILE}")
        print(f"🔍 File exists: {os.path.exists(EMBEDDINGS_FILE)}")
        
        if os.path.exists(EMBEDDINGS_FILE):
            print("Loading pre-computed embeddings...")
            try:
                with open(EMBEDDINGS_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data['chunks']
                    self.chunk_embeddings = data['embeddings']
                print(f"🔍 Loaded {len(self.chunks)} chunks and {len(self.chunk_embeddings)} embeddings")
            except Exception as e:
                print(f"❌ Error loading embeddings: {e}")
                raise
        else:
            print("Creating embeddings using HuggingFace...")
            self.create_embeddings()
            
    def create_embeddings(self):
        """Create embeddings using HuggingFace and save them"""
        print("🔍 Starting embedding creation...")
        # Load documents
        folders = glob.glob("knowledge-base/*")
        print(f"🔍 Found folders: {folders}")
        
        def add_metadata(doc, doc_type):
            doc.metadata["doc_type"] = doc_type
            return doc

        text_loader_kwargs = {'encoding': 'utf-8'}
        documents = []
        
        for folder in folders:
            if os.path.isdir(folder):
                doc_type = os.path.basename(folder)
                print(f"🔍 Processing folder: {folder} (type: {doc_type})")
                loader = DirectoryLoader(folder, glob="*.md", loader_cls=TextLoader, loader_kwargs=text_loader_kwargs)
                folder_docs = loader.load()
                print(f"🔍 Loaded {len(folder_docs)} documents from {folder}")
                documents.extend([add_metadata(doc, doc_type) for doc in folder_docs])

        print(f"🔍 Total documents loaded: {len(documents)}")

        # Split documents into chunks
        print("🔍 Splitting documents into chunks...")
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.chunks = text_splitter.split_documents(documents)
        print(f"🔍 Created {len(self.chunks)} chunks")
        
        # Create embeddings using HuggingFace
        print("🔍 Initializing HuggingFace embeddings model...")
        try:
            embeddings_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            print("✅ HuggingFace embeddings model initialized")
        except Exception as e:
            print(f"❌ Error initializing embeddings model: {e}")
            raise
        
        # Get embeddings for all chunks
        print("🔍 Creating embeddings for all chunks...")
        chunk_texts = [chunk.page_content for chunk in self.chunks]
        try:
            self.chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
            print(f"✅ Created embeddings for {len(self.chunk_embeddings)} chunks")
        except Exception as e:
            print(f"❌ Error creating embeddings: {e}")
            raise
        
        # Save embeddings for future use
        print("🔍 Saving embeddings to file...")
        try:
            with open(EMBEDDINGS_FILE, 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'embeddings': self.chunk_embeddings
                }, f)
            print(f"✅ Saved embeddings for {len(self.chunks)} chunks")
        except Exception as e:
            print(f"❌ Error saving embeddings: {e}")
            raise

# Test initialization
def test_initialization():
    print("🔍 Testing RAG system initialization...")
    try:
        rag_system = RAGSystem()
        rag_system.load_or_create_embeddings()
        print("✅ RAG system initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Error initializing RAG system: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Running debug test...")
    success = test_initialization()
    if success:
        print("🔍 Initialization successful, now testing Gradio...")
        try:
            # Simple test interface
            def simple_response(message, history):
                return f"Echo: {message}"
            
            demo = gr.ChatInterface(simple_response, title="Test Interface")
            print("🔍 About to launch Gradio...")
            demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
        except Exception as e:
            print(f"❌ Error with Gradio: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Initialization failed, cannot proceed")
