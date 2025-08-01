import os
import glob
import gradio as gr
import pickle
from huggingface_hub import InferenceClient
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
DB_NAME = "vector_db"
EMBEDDINGS_FILE = "hf_embeddings.pkl"

# Get Hugging Face token from environment
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

# Initialize the Llama client with token
try:
    client = InferenceClient(MODEL_NAME, token=HF_TOKEN)
    print(f"✅ InferenceClient initialized successfully")
except Exception as e:
    print(f"❌ Error initializing InferenceClient: {e}")
    client = None

class RAGSystem:
    def __init__(self):
        self.embeddings_model = None
        self.vectorstore = None
        self.chunks = []
        self.chunk_embeddings = []
        
    def load_or_create_embeddings(self):
        """Load pre-computed embeddings or create them using OpenAI"""
        if os.path.exists(EMBEDDINGS_FILE):
            print("Loading pre-computed embeddings...")
            with open(EMBEDDINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                self.chunks = data['chunks']
                self.chunk_embeddings = data['embeddings']
        else:
            print("Creating embeddings using OpenAI...")
            self.create_embeddings()
            
    def create_embeddings(self):
        """Create embeddings using OpenAI and save them"""
        # Load documents
        folders = glob.glob("knowledge-base/*")
        
        def add_metadata(doc, doc_type):
            doc.metadata["doc_type"] = doc_type
            return doc

        text_loader_kwargs = {'encoding': 'utf-8'}
        documents = []
        
        for folder in folders:
            if os.path.isdir(folder):
                doc_type = os.path.basename(folder)
                loader = DirectoryLoader(folder, glob="*.md", loader_cls=TextLoader, loader_kwargs=text_loader_kwargs)
                folder_docs = loader.load()
                documents.extend([add_metadata(doc, doc_type) for doc in folder_docs])

        # Split documents into chunks
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.chunks = text_splitter.split_documents(documents)
        
        # Create embeddings using HuggingFace
        embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Get embeddings for all chunks
        chunk_texts = [chunk.page_content for chunk in self.chunks]
        self.chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        
        # Save embeddings for future use
        with open(EMBEDDINGS_FILE, 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'embeddings': self.chunk_embeddings
            }, f)
        
        print(f"Created and saved embeddings for {len(self.chunks)} chunks")
        
    def retrieve_relevant_chunks(self, query, k=5):
        """Retrieve relevant chunks using cosine similarity"""
        if not self.chunk_embeddings:
            return []
            
        # Get embedding for the query
        embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        query_embedding = embeddings_model.embed_query(query)
        
        # Calculate similarities
        similarities = cosine_similarity([query_embedding], self.chunk_embeddings)[0]
        
        # Get top k most similar chunks
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        relevant_chunks = []
        for idx in top_indices:
            chunk_info = {
                'content': self.chunks[idx].page_content,
                'metadata': self.chunks[idx].metadata,
                'similarity': similarities[idx]
            }
            relevant_chunks.append(chunk_info)
            
        return relevant_chunks

# Initialize RAG system
rag_system = RAGSystem()

# Auto-initialize the system for better user experience
def auto_initialize():
    """Auto-initialize the RAG system silently"""
    try:
        rag_system.load_or_create_embeddings()
        print("✅ RAG system auto-initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Error auto-initializing system: {str(e)}")
        return False

def initialize_system():
    """Initialize the RAG system with embeddings"""
    try:
        rag_system.load_or_create_embeddings()
        return "✅ RAG system initialized successfully!"
    except Exception as e:
        return f"❌ Error initializing system: {str(e)}"

def respond_with_rag(message, history):
    """Respond to user query with RAG context - simplified for non-technical users"""
    
    # Validate input
    if not message or not isinstance(message, str) or not message.strip():
        yield "Please enter a question and I'll be happy to help! 😊"
        return
    
    # Ensure history is in the right format
    if history is None:
        history = []
    
    # Automatically initialize system if not done
    if not rag_system.chunk_embeddings:
        yield "Setting up the knowledge base, please wait a moment..."
        try:
            rag_system.load_or_create_embeddings()
        except Exception as e:
            yield "❌ I'm having trouble accessing the company knowledge base right now. Please try again in a moment or contact IT support."
            return
    
    # Build context from RAG
    context = ""
    try:
        relevant_chunks = rag_system.retrieve_relevant_chunks(message, k=5)  # Increased to 5 for more comprehensive context
        if relevant_chunks:
            context = "\n\nRELEVANT INFORMATION FROM BISNER DOCUMENTATION:\n"
            for i, chunk in enumerate(relevant_chunks, 1):
                doc_type = chunk['metadata'].get('doc_type', 'documentation').title()
                similarity_score = chunk['similarity']
                
                # Only include highly relevant chunks (similarity > 0.3)
                if similarity_score > 0.3:
                    context += f"\n--- {doc_type} Documentation (Relevance: {similarity_score:.2f}) ---\n"
                    context += f"{chunk['content']}\n"
                    context += "---\n"
    except Exception as e:
        # Continue without context if retrieval fails
        print(f"Error retrieving context: {e}")
        pass
    
    # Prepare the system message with context
    system_message = """You are a helpful AI assistant for Bisner platform users and administrators. You specialize in providing detailed, accurate information about Bisner's features, modules, and procedures.

IMPORTANT GUIDELINES:
- Provide comprehensive, step-by-step guidance when users ask for help with Bisner features
- Always include relevant links when they are available in the documentation
- When referencing documentation, include the full Public URL if provided
- Structure your responses clearly with headers, bullet points, and numbered steps when appropriate
- If multiple procedures are relevant, mention all of them
- Be specific about whether instructions are for Admins or regular Users
- Include navigation paths clearly (e.g., "Go to Admin → Modules → Service request")
- When mentioning settings or configuration options, be detailed about what each option does
- If there are related topics or additional resources, mention them at the end

RESPONSE FORMAT:
- Start with a brief overview
- Provide step-by-step instructions when applicable
- Include any relevant links from the documentation
- End with benefits or additional tips if appropriate"""
    
    if context:
        system_message += f"\n\nRELEVANT BISNER DOCUMENTATION:\n{context}\n\nBased on this documentation, provide a detailed and helpful response. Include any URLs, step-by-step procedures, and related information that would be useful to the user. Make sure to preserve any links exactly as they appear in the documentation."
    
    # Build conversation history
    messages = [{"role": "system", "content": system_message}]
    
    # Handle different history formats safely
    try:
        for item in history:
            if isinstance(item, dict) and 'role' in item and 'content' in item:
                # New messages format
                if item['role'] in ['user', 'assistant'] and isinstance(item['content'], str):
                    messages.append({"role": item['role'], "content": item['content']})
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                # Legacy tuple format
                if item[0] and isinstance(item[0], str):
                    messages.append({"role": "user", "content": str(item[0])})
                if len(item) > 1 and item[1] and isinstance(item[1], str):
                    messages.append({"role": "assistant", "content": str(item[1])})
    except Exception as e:
        print(f"Error processing history: {e}")
        # Continue with just the system message if history parsing fails

    messages.append({"role": "user", "content": str(message)})

    response = ""
    
    # Check if client is properly initialized
    if client is None:
        yield "❌ The AI service is currently unavailable. Please try again later or contact IT support."
        return
    
    try:
        for message_chunk in client.chat_completion(
            messages,
            max_tokens=1024,  # Increased for more detailed responses
            stream=True,
            temperature=0.6,  # Slightly lower for more focused responses
            top_p=0.9,
        ):
            # Add better error handling for message chunks
            if hasattr(message_chunk, 'choices') and len(message_chunk.choices) > 0:
                if hasattr(message_chunk.choices[0], 'delta') and hasattr(message_chunk.choices[0].delta, 'content'):
                    token = message_chunk.choices[0].delta.content
                    if token and isinstance(token, str):
                        response += token
                        # Ensure we're yielding clean text
                        yield response.strip()
                else:
                    # Handle different response formats
                    continue
            else:
                continue
    except Exception as e:
        print(f"Error in chat completion: {str(e)}")
        yield "❌ I'm having trouble processing your request right now. Please try rephrasing your question or try again in a moment."

# Create a simple, user-friendly Gradio interface
with gr.Blocks(
    title="Insurellm Assistant", 
    theme=gr.themes.Soft(),
    css="""
    .gradio-container {
        max-width: 800px !important;
        margin: auto !important;
    }
    .chat-message {
        font-size: 16px !important;
    }
    """
) as demo:
    # Header
    gr.HTML("""
    <div style="text-align: center; padding: 20px;">
        <h1>🏢 Bisner Assistant</h1>
        <p style="font-size: 18px; color: #666;">
            Your AI-powered company knowledge assistant
        </p>
        <p style="font-size: 14px; color: #888;">
            Ask me anything about Bisner policies, procedures, and company information
        </p>
    </div>
    """)
    
    # Simple chat interface without confusing controls
    chatbot = gr.ChatInterface(
        respond_with_rag,
        title="",
        description="",
        examples=[
            "How do I set up booking restrictions for meeting rooms?",
            "How can I add a new member to a company?",
            "What's the process for creating recurring events?",
            "How do I configure parking access with Brivo integration?",
            "How can I manage service request categories and statuses?",
            "What are the steps to add a new unit to a location?",
            "How do I check past parking reservations for my company?"
        ],
        textbox=gr.Textbox(
            placeholder="Type your question here...", 
            container=False, 
            scale=7
        ),
        chatbot=gr.Chatbot(
            height=500,
            show_label=False,
            container=False,
            type='messages'
        )
    )
    
    # Footer with helpful information
    gr.HTML("""
    <div style="text-align: center; padding: 10px; margin-top: 20px; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #888;">
            💡 Tip: Ask specific questions for better results<br>
            🔒 This assistant uses your company's knowledge base to provide accurate information
        </p>
    </div>
    """)

if __name__ == "__main__":
    # Auto-initialize the system in the background for seamless user experience
    print("🚀 Starting Bisner Assistant...")
    auto_initialize()
    
    # Get port from environment variable for cloud deployment
    port = int(os.environ.get("PORT", 7860))
    
    # Launch with local-friendly settings for development
    print(f"🌐 Launching on port {port}...")
    demo.launch(
        server_name="127.0.0.1",  # Use localhost for local development
        server_port=port,
        share=False,  # Don't create share link in production
        show_error=True,  # Show errors for debugging
        quiet=False  # Show console output for debugging
    )
