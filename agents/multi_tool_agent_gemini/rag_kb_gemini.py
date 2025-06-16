import os
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview import rag
from vertexai.preview.rag import (
    RagCorpus, RagFile, RagEmbeddingModelConfig, RagVectorDbConfig,
    VertexPredictionEndpoint
)
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


scopes =  [
    "https://www.googleapis.com/auth/cloud-platform",                 # broad GCP access
    "https://www.googleapis.com/auth/aiplatform",                     # Vertex AI
    "https://www.googleapis.com/auth/generative-language",            # text-gen & embeddings
    "https://www.googleapis.com/auth/generative-language.retriever", # RAG retrieval & upload
]

class GeminiFAQSystem:
    """
    A comprehensive FAQ system using Gemini AI and Vertex AI RAG.
    
    This version uses the stable Vertex AI APIs without the experimental
    generativeai client to avoid import issues.
    """
    
    def __init__(self, 
                 project_id: str,
                 location: str = "us-central1",
                 service_account_path: Optional[str] = None,
                 corpus_name: str = "FAQ-Knowledge-Base"):
        """
        Initialize the Gemini FAQ System.
        
        Args:
            project_id: GCP Project ID
            location: GCP location for Vertex AI
            service_account_path: Path to service account JSON file
            corpus_name: Name for the RAG corpus
        """
        self.project_id = project_id
        self.location = location
        self.corpus_name = corpus_name
        self.corpus = None
        self.storage_client = None
        self.authed_session = None
        
        # Initialize credentials with explicit scopes (CRITICAL for service accounts)
        if service_account_path and os.path.exists(service_account_path):
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=[
                    "https://www.googleapis.com/auth/cloud-platform",
                    "https://www.googleapis.com/auth/devstorage.read_write"
                    ]
            )
        else:
            # Use Application Default Credentials with explicit scopes
            from google.auth import default
            self.credentials, _ = default(scopes=scopes)
            logger.info("Using Application Default Credentials with explicit scopes")
        
        self._initialize_clients()
        self._setup_corpus()
    
    def _initialize_clients(self):
        """Initialize all required GCP clients."""
        try:
            # Initialize Vertex AI
            vertexai.init(
                project=self.project_id,
                location=self.location,
                credentials=self.credentials
            )
            
            # Initialize Storage client for document management
            self.storage_client = storage.Client(
                project=self.project_id,
                credentials=self.credentials
            )
            
            # Initialize authorized session for RAG API calls
            self.authed_session = AuthorizedSession(self.credentials)
            
            logger.info("✅ All clients initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize clients: {str(e)}")
            raise
    
    def _setup_corpus(self):
        """Set up or retrieve existing RAG corpus."""
        try:
            # Check for existing corpus
            existing_corpora = list(rag.list_corpora())
            existing = [c for c in existing_corpora if c.display_name == self.corpus_name]
            
            if existing:
                self.corpus = existing[0]
                logger.info(f"📂 Using existing corpus: {self._get_safe_corpus_metadata()['corpus_name']}")
            else:
                # Create new corpus with embedding model
                embedding_model_config = RagEmbeddingModelConfig(
                    vertex_prediction_endpoint=VertexPredictionEndpoint(
                        publisher_model="publishers/google/models/text-embedding-005"
                    )
                )
                
                self.corpus = rag.create_corpus(
                    display_name=self.corpus_name,
                    backend_config=RagVectorDbConfig(
                        rag_embedding_model_config=embedding_model_config
                    ),
                )
                logger.info(f"✅ Created new corpus: {self._get_safe_corpus_metadata()['corpus_name']}")
                
        except Exception as e:
            logger.error(f"❌ Failed to setup corpus: {str(e)}")
            raise
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file for deduplication."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _get_existing_file_hashes(self) -> Dict[str, str]:
        """Get hashes of existing files in the corpus."""
        existing_files = {}
        try:
            files = list(rag.list_files(corpus_name=self._get_safe_corpus_metadata()['corpus_name']))
            for file in files:
                # Store mapping of file hash to file name
                if hasattr(file, 'description') and file.description:
                    # Extract hash from description if stored
                    if file.description.startswith("hash:"):
                        hash_value = file.description.replace("hash:", "")
                        existing_files[hash_value] = file.display_name
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve existing file hashes: {str(e)}")
        
        return existing_files
    def _get_safe_corpus_metadata(self) -> Dict[str, str]:
        """Get safe metadata for the corpus."""
        assert self.corpus is not None, "Corpus must be initialized before getting metadata"
        try:
            metadata = {
                "project_id": self.project_id,
                "location": self.location,
                "corpus_name": self.corpus.name,
                "created_at": datetime.now().isoformat(),
                "display_name": self.corpus.display_name,
            }
            return metadata
        except Exception as e:
            logger.error(f"❌ Failed to get corpus metadata: {str(e)}")
            return {"error": str(e)}
    
    def update(self, 
               documents_path: str,
               file_extensions: List[str] = [".md", ".txt", ".pdf"],
               batch_size: int = 10) -> Dict[str, int]:
        """
        Update the knowledge base with new documents.
        
        Args:
            documents_path: Path to directory containing documents
            file_extensions: List of file extensions to process
            batch_size: Number of files to process in each batch
            
        Returns:
            Dictionary with upload statistics
        """
        stats = {"uploaded": 0, "skipped": 0, "failed": 0}
        
        try:
            # Get existing file hashes for deduplication
            existing_hashes = self._get_existing_file_hashes()
            
            # Find all documents to process
            documents_to_process = []
            for ext in file_extensions:
                pattern = f"**/*{ext}"
                documents_to_process.extend(Path(documents_path).glob(pattern))
            
            if not documents_to_process:
                logger.warning(f"⚠️ No documents found in {documents_path}")
                return stats
            
            logger.info(f"📄 Found {len(documents_to_process)} documents to process")
            
            # Process documents in batches
            for i in range(0, len(documents_to_process), batch_size):
                batch = documents_to_process[i:i + batch_size]
                
                for doc_path in batch:
                    try:
                        # Calculate file hash for deduplication
                        file_hash = self._calculate_file_hash(str(doc_path))
                        
                        if file_hash in existing_hashes:
                            logger.info(f"⏭️ Skipping duplicate: {doc_path.name}")
                            stats["skipped"] += 1
                            continue
                        
                        # Upload new document
                        relative_path = doc_path.relative_to(documents_path)
                        display_name = str(relative_path)
                        description = f"hash:{file_hash}"
                        
                        rag.upload_file(
                            corpus_name=self._get_safe_corpus_metadata()['corpus_name'],
                            path=str(doc_path),
                            display_name=display_name,
                            description=description
                        )
                        
                        logger.info(f"✅ Uploaded: {display_name}")
                        stats["uploaded"] += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to upload {doc_path}: {str(e)}")
                        stats["failed"] += 1
            
            logger.info(f"📊 Upload complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Update failed: {str(e)}")
            raise
    
    def _retrieve_contexts(self, query: str, max_contexts: int = 5) -> List[str]:
        """Retrieve relevant contexts from the RAG corpus."""
        try:
            parent = f"projects/{self.project_id}/locations/{self.location}"
            endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1/{parent}:retrieveContexts"
            
            body = {
                "vertexRagStore": {
                    "ragResources": [{"ragCorpus": self._get_safe_corpus_metadata()['corpus_name']}]
                },
                "query": {"text": query},
                "similarityTopK": max_contexts
            }
            assert self.authed_session is not None, "Authorized session must be initialized"
            response = self.authed_session.post(endpoint, json=body)
            response.raise_for_status()
            data = response.json()
            
            # Extract contexts
            contexts = []
            for ctx in data.get("contexts", {}).get("contexts", []):
                text = ctx.get("text") or ctx.get("content") or ""
                if text.strip():
                    contexts.append(text.strip())
            
            return contexts
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve contexts: {str(e)}")
            return []
    
    def answer(self, 
               question: str,
               system_prompt: Optional[str] = None,
               max_contexts: int = 5,
               temperature: float = 0.3) -> str:
        """
        Generate an answer to a question using RAG and Gemini.
        
        Args:
            question: User's question
            system_prompt: Custom system prompt (optional)
            max_contexts: Maximum number of contexts to retrieve
            temperature: Generation temperature (0.0 to 1.0)
            
        Returns:
            Generated answer
        """
        try:
            # Retrieve relevant contexts
            contexts = self._retrieve_contexts(question, max_contexts)
            
            if not contexts:
                return "I couldn't find relevant information to answer your question. Please try rephrasing or check if the knowledge base contains information about this topic."
            
            # Build prompt
            if system_prompt is None:
                system_prompt = """You are a helpful AI assistant that answers questions based on provided knowledge base sources. 

Instructions:
- Use only the information provided in the sources below
- If the answer is not in the sources, say so clearly
- Cite sources using [Source X] format
- Be concise but comprehensive
- If multiple sources conflict, mention the discrepancy"""

            prompt = f"{system_prompt}\n\n"
            
            # Add contexts with source numbers
            for i, context in enumerate(contexts, 1):
                prompt += f"Source {i}: {context}\n\n"
            
            prompt += f"Question: {question}\n\nAnswer:"
            
            # Generate response using Vertex AI GenerativeModel
            model = GenerativeModel("gemini-2.0-flash-001")
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Failed to generate answer: {str(e)}")
            return f"I encountered an error while processing your question: {str(e)}"
    
    def chat(self, 
             question: str,
             conversation_history: Optional[List[Dict[str, str]]] = None,
             system_prompt: Optional[str] = None) -> Tuple[str, List[Dict[str, str]]]:
        """
        Chat interface with conversation history.
        
        Args:
            question: User's question
            conversation_history: Previous conversation history
            system_prompt: Custom system prompt
            
        Returns:
            Tuple of (answer, updated_conversation_history)
        """
        if conversation_history is None:
            conversation_history = []
        
        # For chat, we can include recent conversation context
        chat_system_prompt = system_prompt or """You are a helpful AI assistant that answers questions based on provided knowledge base sources.

Instructions:
- Use the information from the knowledge base sources below
- Consider the conversation history for context
- Provide helpful, conversational responses
- Cite sources using [Source X] format when referencing specific information
- If you don't know something, say so clearly"""
        
        # Generate answer
        answer = self.answer(question, chat_system_prompt)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": question})
        conversation_history.append({"role": "assistant", "content": answer})
        
        # Keep only last 10 exchanges to manage context length
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        return answer, conversation_history
    
    def llm(self, 
            prompt: str,
            model_name: str = "gemini-2.0-flash-001",
            temperature: float = 0.7) -> str:
        """
        Direct access to the LLM for custom prompts.
        
        Args:
            prompt: Direct prompt to the model
            model_name: Name of the Gemini model to use
            temperature: Generation temperature
            
        Returns:
            Generated response
        """
        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            return response.text
            
        except Exception as e:
            logger.error(f"❌ LLM call failed: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_corpus_info(self) -> Dict:
        """Get information about the current corpus."""
        try:
            files = list(rag.list_files(corpus_name=self._get_safe_corpus_metadata()['corpus_name']))
            return {
                "corpus_name": self._get_safe_corpus_metadata()['display_name'],
                "corpus_id": self._get_safe_corpus_metadata()['corpus_name'],
                "total_files": len(files),
                "file_names": [f.display_name for f in files],
                "created_at": getattr(self.corpus, 'create_time', 'Unknown'),
            }
        except Exception as e:
            logger.error(f"❌ Failed to get corpus info: {str(e)}")
            return {"error": str(e)}
    
    def delete_corpus(self):
        """Delete the current corpus (use with caution!)."""
        try:
            if self.corpus:
                rag.delete_corpus(name=self._get_safe_corpus_metadata()['corpus_name'])
                logger.info(f"🗑️ Deleted corpus: {self._get_safe_corpus_metadata()['corpus_name']}")
                self.corpus = None
            else:
                logger.warning("⚠️ No corpus to delete")
        except Exception as e:
            logger.error(f"❌ Failed to delete corpus: {str(e)}")
            raise