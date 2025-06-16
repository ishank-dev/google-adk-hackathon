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
                 gcs_bucket: Optional[str] = None,
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
        self.storage_bucket = gcs_bucket or f"{project_id}-rag-corpus-bucket"
        
        # Initialize credentials with explicit scopes (CRITICAL for service accounts)
        if service_account_path and os.path.exists(service_account_path):
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=[
                    "https://www.googleapis.com/auth/cloud-platform",
                    "https://www.googleapis.com/auth/devstorage.read_write",
                ]
            )
        else:
            # ADC already have cloud-platform by default
            from google.auth import default
            self.credentials, _ = default()
        
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
    
    def _get_existing_file_hashes(self) -> Dict[str, str]:
        """
        Get hashes of existing files from GCS blob metadata.
        Returns dict mapping hash -> filename for deduplication.
        """
        existing_files = {}
        
        try:
            if self.storage_client:
                bucket = self.storage_client.bucket(self.storage_bucket)
                blobs = bucket.list_blobs(prefix=f"{self.corpus_name}/")
                
                for blob in blobs:
                    # Reload blob to get metadata
                    blob.reload()
                    if blob.metadata and "file_hash" in blob.metadata:
                        file_hash = blob.metadata["file_hash"]
                        filename = blob.name.replace(f"{self.corpus_name}/", "")
                        existing_files[file_hash] = filename
                    else:
                        # For existing files without metadata, calculate hash from filename + size
                        # This is a fallback for files uploaded before implementing hash tracking
                        fallback_hash = hashlib.sha256(f"{blob.name}_{blob.size}".encode()).hexdigest()
                        filename = blob.name.replace(f"{self.corpus_name}/", "")
                        existing_files[fallback_hash] = filename
                        logger.debug(f"📝 Using fallback hash for existing file: {filename}")
                        
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve existing file hashes from GCS: {str(e)}")
        
        return existing_files

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file for deduplication."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ Failed to calculate hash for {file_path}: {str(e)}")
            # Return a fallback hash based on filename and modification time
            import time
            fallback_string = f"{file_path}_{os.path.getmtime(file_path)}"
            return hashlib.sha256(fallback_string.encode()).hexdigest()

    def rebuild_hash_metadata(self, documents_path: str) -> Dict[str, int]:
        """
        Rebuild hash metadata for existing GCS files by matching with local files.
        Useful when upgrading to the hash-based deduplication system.
        """
        stats = {"updated": 0, "matched": 0, "failed": 0}
        
        try:
            if not self.storage_client:
                logger.error("❌ Storage client not initialized")
                return stats
                
            bucket = self.storage_client.bucket(self.storage_bucket)
            blobs = list(bucket.list_blobs(prefix=f"{self.corpus_name}/"))
            
            # Get all local files
            local_files = {}
            docs_path = Path(documents_path)
            for file_path in docs_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(docs_path).as_posix()
                    local_files[rel_path] = file_path
            
            for blob in blobs:
                try:
                    filename = blob.name.replace(f"{self.corpus_name}/", "")
                    
                    # Skip if already has hash metadata
                    blob.reload()
                    if blob.metadata and "file_hash" in blob.metadata:
                        stats["matched"] += 1
                        continue
                    
                    # Find matching local file
                    if filename in local_files:
                        local_file_hash = self._calculate_file_hash(str(local_files[filename]))
                        
                        # Update blob metadata
                        if not blob.metadata:
                            blob.metadata = {}
                        blob.metadata["file_hash"] = local_file_hash
                        blob.patch()
                        
                        stats["updated"] += 1
                        logger.info(f"✅ Updated hash for: {filename}")
                    else:
                        logger.warning(f"⚠️ No local file found for: {filename}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to update hash for {blob.name}: {str(e)}")
                    stats["failed"] += 1
                    
        except Exception as e:
            logger.error(f"❌ Failed to rebuild hash metadata: {str(e)}")
            
        logger.info(f"📊 Hash metadata rebuild complete: {stats}")
        return stats

    def clear_corpus_files(self) -> Dict[str, int]:
        """
        Remove all files from the corpus (useful for testing or cleanup).
        Returns stats about deletion.
        """
        stats = {"deleted": 0, "failed": 0}
        
        try:
            files = list(rag.list_files(corpus_name=self._get_safe_corpus_metadata()['corpus_name']))
            
            for file in files:
                try:
                    rag.delete_file(name=file.name)
                    stats["deleted"] += 1
                    logger.info(f"🗑️ Deleted: {file.display_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to delete {file.display_name}: {str(e)}")
                    stats["failed"] += 1
                    
        except Exception as e:
            logger.error(f"❌ Failed to list files for deletion: {str(e)}")
            
        logger.info(f"📊 Deletion complete: {stats}")
        return stats

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
        Update the RAG corpus with documents, using hash-based deduplication.
        """
        stats = {"uploaded": 0, "skipped": 0, "failed": 0}
        assert self.storage_client is not None, "Storage client must be initialized"
        bucket = self.storage_client.bucket(self.storage_bucket)

        # Get existing file hashes for deduplication
        existing_hashes = self._get_existing_file_hashes()
        logger.info(f"📋 Found {len(existing_hashes)} existing files in corpus")

        # Gather all files matching extensions
        docs = []
        for ext in file_extensions:
            docs.extend(Path(documents_path).rglob(f"*{ext}"))
        if not docs:
            logger.warning(f"⚠️ No docs found in {documents_path}")
            return stats

        for i in range(0, len(docs), batch_size):
            for doc in docs[i : i + batch_size]:
                try:
                    rel_path = doc.relative_to(documents_path).as_posix()
                    
                    # Calculate file hash for deduplication
                    file_hash = self._calculate_file_hash(str(doc))
                    
                    # Check if file already exists (by hash)
                    if file_hash in existing_hashes:
                        logger.info(f"⏭️ Skipped (duplicate): {rel_path}")
                        stats["skipped"] += 1
                        continue
                    
                    gcs_path = f"{self.corpus_name}/{rel_path}"
                    gs_uri = f"gs://{self.storage_bucket}/{gcs_path}"

                    # 1️⃣ Upload to GCS
                    blob = bucket.blob(gcs_path)
                    blob.upload_from_filename(str(doc))
                    
                    # Store hash in blob metadata for future deduplication
                    blob.metadata = {"file_hash": file_hash}
                    blob.patch()

                    # 2️⃣ Import into RAG corpus
                    rag.import_files(
                        self._get_safe_corpus_metadata()['corpus_name'],
                        paths=[gs_uri],
                        transformation_config=rag.TransformationConfig(
                            chunking_config=rag.ChunkingConfig(
                                chunk_size=512, 
                                chunk_overlap=100
                            )
                        )
                    )

                    logger.info(f"✅ Imported: {rel_path} (hash: {file_hash[:8]}...)")
                    stats["uploaded"] += 1
                    
                    # Add to existing hashes to prevent duplicates in same batch
                    existing_hashes[file_hash] = rel_path

                except Exception as e:
                    logger.error(f"❌ {doc.name} → {e}")
                    stats["failed"] += 1

        logger.info(f"📊 Update done: {stats}")
        return stats

    
    def _retrieve_contexts(self, query: str, max_contexts: int = 5) -> List[str]:
        """Retrieve relevant contexts from the RAG corpus."""
        try:
            # Use v1beta1 API version (not v1)
            parent = f"projects/{self.project_id}/locations/{self.location}"
            endpoint = f"https://{self.location}-aiplatform.googleapis.com/v1beta1/{parent}:retrieveContexts"
            
            # Correct request body format based on the latest API docs
            body = {
                "vertex_rag_store": {  # Note: underscore, not camelCase
                    "rag_resources": [  # This should be an array
                        {
                            "rag_corpus": self._get_safe_corpus_metadata()['corpus_name']
                        }
                    ]
                },
                "query": {
                    "text": query,
                    "similarity_top_k": max_contexts  # This should be inside query object
                }
            }
            
            assert self.authed_session is not None, "Authorized session must be initialized"
            response = self.authed_session.post(endpoint, json=body)
            
            # Debug logging to help troubleshoot
            if response.status_code != 200:
                logger.error(f"❌ API Error {response.status_code}: {response.text}")
                logger.error(f"Request body was: {json.dumps(body, indent=2)}")
                response.raise_for_status()
                
            data = response.json()
            logger.debug(f"📥 Retrieved response: {json.dumps(data, indent=2)}")
            
            # Extract contexts from the response
            contexts = []
            
            # Check if the response structure matches expected format
            if "contexts" in data:
                if "contexts" in data["contexts"]:
                    # Nested structure: {"contexts": {"contexts": [...]}}
                    context_list = data["contexts"]["contexts"]
                else:
                    # Direct structure: {"contexts": [...]}
                    context_list = data["contexts"]
                    
                for ctx in context_list:
                    # Try different possible field names for the text content
                    text = (ctx.get("text") or 
                            ctx.get("content") or 
                            ctx.get("source_uri", ""))
                    
                    if text and text.strip():
                        contexts.append(text.strip())
            
            logger.info(f"📚 Retrieved {len(contexts)} contexts for query: '{query[:50]}...'")
            return contexts
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve contexts: {str(e)}")
            # If it's a requests error, log more details
            if hasattr(e, 'response'):
                logger.error(f"Response status: {e.response.status_code}") # type: ignore
                logger.error(f"Response body: {e.response.text}") # type: ignore
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
                system_prompt = """
                You are a helpful AI assistant that answers questions based on provided knowledge base sources. 
                Instructions:
                - Use only the information provided in the sources below
                - If the answer is not in the sources, say so clearly
                - Cite sources using [Source X] format
                - Be concise but comprehensive
                - If multiple sources conflict, mention the discrepancy
                """

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