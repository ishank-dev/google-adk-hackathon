# OpenAI RAG Agent with Knowledge Base
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

# Load environment variables
load_dotenv()
from pathlib import Path

# Use vector database at project root level
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Go up to project root (agents/openai_agent/ -> agents/ -> root)
db_name = str(BASE_DIR / "vector_db_openai")  # Use absolute path to project root

# Use shared knowledge base at root level
DOC_DIR = BASE_DIR / "knowledge-base-slack"          # Shared knowledge base
folders = [p for p in DOC_DIR.iterdir() if p.is_dir()]

if not folders:
    raise FileNotFoundError(
        f"No Markdown folders found under {DOC_DIR}. "
        "Check the path or ensure knowledge-base-slack exists at root level."
    )

def add_metadata(doc, doc_type):
    """Add document type metadata"""
    doc.metadata["doc_type"] = doc_type
    return doc

# Load documents from all folders
text_loader_kwargs = {'encoding': 'utf-8'}
documents = []

for folder in folders:
    doc_type = os.path.basename(folder)
    loader = DirectoryLoader(folder, glob="**/*.md", loader_cls=TextLoader, loader_kwargs=text_loader_kwargs)
    folder_docs = loader.load()
    documents.extend([add_metadata(doc, doc_type) for doc in folder_docs])

# Split documents into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(documents)

print(f"Total number of chunks: {len(chunks)}")

# Document types found
doc_types = set(doc.metadata.get("doc_type", "unknown") for doc in documents)
print(f"Document types found: {doc_types}")

# Initialize HuggingFace embeddings (for fair comparison with Llama agent)
try:
    from langchain.embeddings import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Create or load vector store - PERFORMANCE OPTIMIZED
print(f"Checking vector database: {db_name}")

if os.path.exists(db_name):
    print("✅ Found existing vector database - loading from cache")
    vectorstore = Chroma(persist_directory=db_name, embedding_function=embeddings)
    
    # Verify the database has content
    try:
        count = vectorstore._collection.count()
        if count == 0:
            print("⚠️ Vector database is empty - rebuilding...")
            vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=db_name)
        else:
            print(f"✅ Using cached vectors: {count} documents ready")
    except Exception as e:
        print(f"⚠️ Vector database corrupted ({e}) - rebuilding...")
        vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=db_name)
else:
    print("🔄 Creating new vector database (this may take 30-60 seconds)...")
    vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=db_name)
    print("✅ Vector database created and persisted")

print(f"Vectorstore created with {len(chunks)} documents")

# Check vector count
try:
    count = vectorstore._collection.count()
    print(f"There are {count} vectors with {embeddings.client.get_sentence_embedding_dimension() if hasattr(embeddings, 'client') else '384'} dimensions in the vector store")
except:
    print("Vector count check not available")

# Document types in vectorstore
try:
    result = vectorstore._collection.get()
    doc_types_in_store = set(meta.get("doc_type", "unknown") for meta in result["metadatas"])
    print(doc_types_in_store)
except:
    print("Could not retrieve document types from vectorstore")

# Initialize OpenAI LLM
# Initialize OpenAI LLM - Using the correct parameter name
llm = ChatOpenAI(temperature=0.7, model='gpt-4o', max_tokens=2000)

# Create enhanced conversation chain (same as enhanced Llama agent)
memory = ConversationBufferMemory(
    memory_key='chat_history', 
    return_messages=True,
    output_key='answer'  # Key enhancement for proper memory handling
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})  # Top 5 relevant docs

conversation_chain = ConversationalRetrievalChain.from_llm(
    llm=llm, 
    retriever=retriever, 
    memory=memory,
    return_source_documents=True,  # Include source documents
    verbose=True  # Enable verbose output to see reformulation
)

def chat(question: str, history=None):
    """
    Chat function for OpenAI RAG agent with enhanced conversation handling
    """
    try:
        if history is None:
            history = []
        
        # The ConversationalRetrievalChain handles question reformulation automatically
        # when verbose=True and proper memory is configured
        result = conversation_chain.invoke({
            "question": question, 
            "chat_history": history
        })
        
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
        
        return answer
        
    except Exception as e:
        error_msg = f"Error in OpenAI agent: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return error_msg

def create_interface():
    """Create Gradio interface for OpenAI agent"""
    with gr.Blocks(title="OpenAI RAG Agent", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🤖 OpenAI RAG Agent (GPT-4o)")
        gr.Markdown("Ask questions about your knowledge base using GPT-4o with enhanced conversation handling.")
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="OpenAI Agent Response",
                    height=500,
                    show_label=True
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your Question",
                        placeholder="Ask about events, locations, parking, platform, or service requests...",
                        scale=4
                    )
                    submit_btn = gr.Button("Ask OpenAI", variant="primary", scale=1)
                
                clear_btn = gr.Button("Clear Conversation")
                
            with gr.Column(scale=1):
                gr.Markdown("### 💡 Sample Questions")
                sample_questions = [
                    "How do I book a parking space?",
                    "What's the process for organizing an event?",
                    "How do I submit a service request?",
                    "Where can I find location information?",
                    "How do I access the platform?"
                ]
                
                for question in sample_questions:
                    sample_btn = gr.Button(question, size="sm")
                    sample_btn.click(
                        lambda q=question: q,
                        outputs=msg
                    )
                
                gr.Markdown("### 📊 Agent Info")
                gr.Markdown(f"""
                - **Model**: GPT-4o (OpenAI)
                - **Embeddings**: HuggingFace all-MiniLM-L6-v2
                - **Documents**: {len(chunks)}
                - **Retrieval**: Top 5 relevant chunks
                - **Features**: Conversation reformulation, Source citations
                """)
        
        def respond(message, history):
            if not message.strip():
                return history, ""
            
            bot_message = chat(message, history)
            history.append((message, bot_message))
            return history, ""
        
        def clear_conversation():
            global conversation_chain
            if conversation_chain:
                # Reset memory
                conversation_chain.memory.clear()
            return []
        
        submit_btn.click(respond, [msg, chatbot], [chatbot, msg])
        msg.submit(respond, [msg, chatbot], [chatbot, msg])
        clear_btn.click(clear_conversation, outputs=chatbot)
    
    return interface

if __name__ == "__main__":
    # Create and launch the interface
    openai_interface = create_interface()
    
    print("🌐 Launching OpenAI Agent interface...")
    print("📝 You can now ask questions with enhanced conversation handling!")
    print("🔗 The interface will open in your browser")
    
    openai_interface.launch(
        server_name="127.0.0.1",
        server_port=7861,  # Different port from Llama agent
        share=False,
        show_error=True
    )
