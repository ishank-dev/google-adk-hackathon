import os
import json
import hashlib
from typing import Any, List, Dict, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime
import tempfile

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview import rag
from vertexai.preview.rag import (
    RagEmbeddingModelConfig, RagVectorDbConfig,
    VertexPredictionEndpoint
)
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from agents.messaging_agent.utils.config import env_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


scopes =  [
    "https://www.googleapis.com/auth/cloud-platform",                 # broad GCP access
    "https://www.googleapis.com/auth/aiplatform",                     # Vertex AI
    "https://www.googleapis.com/auth/generative-language",            # text-gen & embeddings
    "https://www.googleapis.com/auth/generative-language.retriever", # RAG retrieval & upload
]

base_system_prompt = """
You are a helpful AI assistant that answers questions based on provided knowledge base sources.

SAFETY GUIDELINES:
- REFUSE to answer questions that involve:
  * Instructions for creating weapons, explosives, or dangerous devices
  * Detailed methods for illegal activities (drug manufacturing, fraud schemes, etc.)
  * Specific instructions for self-harm or harming others
  * Malicious hacking techniques or exploit code
  * Inappropriate sexual content involving minors
- For factual, educational information about these topics (like historical context or general awareness), use your judgment
- If you must refuse a question for safety reasons, respond with: "I can't provide information on this topic for safety reasons."

ANSWERING GUIDELINES:
- Prioritize information from the provided sources below
- You may use basic reasoning and general knowledge to contextualize source information
- If the specific answer is not available in the sources, state: "I don't have information about this in my knowledge base."
- Be concise but comprehensive
- Stay focused on the question asked
- Maintain a helpful and professional tone

ERROR HANDLING:
- For any question where the knowledge base lacks sufficient information, mention: "I don't have information about this in my knowledge base."
- For any question that you are not able to provide answer with other than the safety questions, mention: "I don't have enough information to answer this question."
- No unanswered questions other than safety refusals should miss either of the above two statements.
Remember: Prioritize safety, then provide accurate responses based on available sources while being transparent about limitations.
"""

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

    def _calculate_content_hash(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Calculate SHA-256 hash of content string for deduplication."""
        hash_sha256 = hashlib.sha256()
        
        # Include content
        hash_sha256.update(content.encode('utf-8'))
        
        # Include relevant metadata for uniqueness (optional)
        if metadata:
            # Sort metadata keys for consistent hashing
            metadata_str = json.dumps(metadata, sort_keys=True)
            hash_sha256.update(metadata_str.encode('utf-8'))
        
        return hash_sha256.hexdigest()

    def _normalize_content_for_similarity(self, content: str) -> str:
        """Normalize content for semantic similarity comparison."""
        import re
        
        # Convert to lowercase
        normalized = content.lower()
        
        # Remove extra whitespace and normalize line breaks
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation that doesn't affect meaning
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Strip leading/trailing whitespace
        normalized = normalized.strip()
        
        return normalized

    async def _check_semantic_similarity(self, new_content: str, similarity_threshold: float = 0.85) -> Optional[Dict]:
        """
        Check if new content is semantically similar to existing documents.
        
        Args:
            new_content: Content to check for similarity
            similarity_threshold: Minimum cosine similarity to consider duplicate (0.0 to 1.0)
            
        Returns:
            Dict with similarity info if duplicate found, None otherwise
        """
        try:
            from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Get embedding model
            embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            
            # Normalize new content
            normalized_new = self._normalize_content_for_similarity(new_content)
            
            # Get embedding for new content
            new_embedding_input = TextEmbeddingInput(text=normalized_new, task_type="RETRIEVAL_DOCUMENT")
            new_embeddings = embedding_model.get_embeddings([new_embedding_input])
            new_vector = np.array(new_embeddings[0].values).reshape(1, -1)
            
            # Get existing documents from GCS and check similarity
            if not self.storage_client:
                return None
                
            bucket = self.storage_client.bucket(self.storage_bucket)
            blobs = bucket.list_blobs(prefix=f"{self.corpus_name}/documents/")
            
            for blob in blobs:
                try:
                    # Skip if no metadata
                    blob.reload()
                    if not blob.metadata:
                        continue
                    
                    # Get stored embedding if available, otherwise compute it
                    stored_embedding = blob.metadata.get("content_embedding")
                    
                    if not stored_embedding:
                        # Download and get content for comparison
                        content = blob.download_as_text(encoding='utf-8')
                        
                        # Extract actual content (skip metadata header)
                        lines = content.split('\n')
                        actual_content_start = 0
                        for i, line in enumerate(lines):
                            if line.strip() == "" and i > 0:  # Empty line after metadata
                                actual_content_start = i + 1
                                break
                        
                        actual_content = '\n'.join(lines[actual_content_start:])
                        normalized_existing = self._normalize_content_for_similarity(actual_content)
                        
                        # Get embedding for existing content
                        existing_embedding_input = TextEmbeddingInput(text=normalized_existing, task_type="RETRIEVAL_DOCUMENT")
                        existing_embeddings = embedding_model.get_embeddings([existing_embedding_input])
                        existing_vector = np.array(existing_embeddings[0].values).reshape(1, -1)
                        
                        # Store embedding in metadata for future use
                        blob.metadata["content_embedding"] = ",".join(map(str, existing_embeddings[0].values))
                        blob.patch()
                    else:
                        # Use stored embedding
                        existing_vector = np.array([float(x) for x in stored_embedding.split(",")]).reshape(1, -1)
                    
                    # Calculate cosine similarity
                    similarity = cosine_similarity(new_vector, existing_vector)[0][0]
                    
                    if similarity >= similarity_threshold:
                        return {
                            "similar_file": blob.name.replace(f"{self.corpus_name}/documents/", ""),
                            "similarity_score": float(similarity),
                            "original_title": blob.metadata.get("original_title", "Unknown"),
                            "existing_hash": blob.metadata.get("file_hash", "Unknown")
                        }
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error checking similarity for {blob.name}: {str(e)}")
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Semantic similarity check failed: {str(e)}")
            return None

    async def add_document(self, 
                    content: str, 
                    title: str,
                    doc_type: str = "text", 
                    metadata: Optional[Dict] = None,
                    chunk_size: int = 512,
                    chunk_overlap: int = 100,
                    similarity_threshold: float = 0.85,
                    enable_semantic_dedup: bool = True) -> Dict[str, Any]:
        """
        Add a document directly from content string with advanced deduplication.
        
        Args:
            content: The text content to add
            title: Title/filename for the document
            doc_type: Type of document (e.g., 'text', 'markdown', 'slack_message')
            metadata: Additional metadata to store
            chunk_size: Size of chunks for RAG processing
            chunk_overlap: Overlap between chunks
            similarity_threshold: Cosine similarity threshold for semantic deduplication (0.0 to 1.0)
            enable_semantic_dedup: Whether to enable semantic similarity checking
            
        Returns:
            Dict with status, hash, similarity info, and processing details
        """
        stats = {"uploaded": 0, "skipped": 0, "failed": 0}
        
        try:
            assert self.storage_client is not None, "Storage client must be initialized"
            bucket = self.storage_client.bucket(self.storage_bucket)
            
            # Prepare metadata
            doc_metadata = {
                "title": title,
                "doc_type": doc_type,
                "created_at": datetime.now().isoformat(),
                "content_length": len(content),
                **(metadata or {})
            }
            
            # Calculate content hash for exact deduplication
            content_hash = self._calculate_content_hash(content, doc_metadata)
            
            # Get existing file hashes for exact deduplication
            existing_hashes = self._get_existing_file_hashes()
            
            # Check for exact duplicates first (faster)
            if content_hash in existing_hashes:
                logger.info(f"⏭️ Skipped (exact duplicate): {title}")
                stats["skipped"] += 1
                return {
                    "status": "skipped",
                    "reason": "exact_duplicate",
                    "hash": content_hash,
                    "existing_file": existing_hashes[content_hash],
                    "stats": stats
                }
            
            # Check for semantic similarity if enabled
            similarity_result = None
            if enable_semantic_dedup:
                similarity_result = await self._check_semantic_similarity(content, similarity_threshold)
                
                if similarity_result:
                    logger.info(f"⏭️ Skipped (semantic duplicate): {title} (similarity: {similarity_result['similarity_score']:.3f})")
                    stats["skipped"] += 1
                    return {
                        "status": "skipped",
                        "reason": "semantic_duplicate",
                        "hash": content_hash,
                        "similarity_info": similarity_result,
                        "stats": stats
                    }
            
            # Create temporary file with content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                # Write metadata as header comment
                temp_file.write(f"# Document: {title}\n")
                temp_file.write(f"# Type: {doc_type}\n")
                temp_file.write(f"# Created: {doc_metadata['created_at']}\n")
                if metadata:
                    for key, value in metadata.items():
                        temp_file.write(f"# {key}: {value}\n")
                temp_file.write("\n")
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Generate unique filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{safe_title}_{timestamp}_{content_hash[:8]}.txt"
                
                gcs_path = f"{self.corpus_name}/documents/{filename}"
                gs_uri = f"gs://{self.storage_bucket}/{gcs_path}"
                
                # 1️⃣ Upload to GCS
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(temp_file_path)
                
                # Store hash, metadata, and embedding in blob metadata for future deduplication
                blob.metadata = {
                    "file_hash": content_hash,
                    "original_title": title,
                    "doc_type": doc_type,
                    "created_at": doc_metadata['created_at'],
                    "content_length": str(len(content))
                }
                
                # Store content embedding for future semantic similarity checks
                if enable_semantic_dedup:
                    try:
                        from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
                        embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
                        normalized_content = self._normalize_content_for_similarity(content)
                        embedding_input = TextEmbeddingInput(text=normalized_content, task_type="RETRIEVAL_DOCUMENT")
                        embeddings = embedding_model.get_embeddings([embedding_input])
                        blob.metadata["content_embedding"] = ",".join(map(str, embeddings[0].values))
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to store embedding: {str(e)}")
                
                if metadata:
                    # Add custom metadata with prefix to avoid conflicts
                    for key, value in metadata.items():
                        blob.metadata[f"custom_{key}"] = str(value)
                
                blob.patch()
                
                # 2️⃣ Import into RAG corpus
                rag.import_files(
                    self._get_safe_corpus_metadata()['corpus_name'],
                    paths=[gs_uri],
                    transformation_config=rag.TransformationConfig(
                        chunking_config=rag.ChunkingConfig(
                            chunk_size=chunk_size, 
                            chunk_overlap=chunk_overlap
                        )
                    )
                )
                
                logger.info(f"✅ Added document: {title} (hash: {content_hash[:8]}...)")
                stats["uploaded"] += 1
                
                return {
                    "status": "success",
                    "hash": content_hash,
                    "filename": filename,
                    "gcs_path": gcs_path,
                    "gs_uri": gs_uri,
                    "stats": stats,
                    "metadata": doc_metadata
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"❌ Failed to add document '{title}': {str(e)}")
            stats["failed"] += 1
            return {
                "status": "error",
                "error": str(e),
                "stats": stats
            }

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
               temperature: float = 0.3,
               enable_fallback: bool = True) -> str:
        """
        Generate an answer to a question using RAG and Gemini.
        
        Args:
            question: User's question
            system_prompt: Custom system prompt (optional)
            max_contexts: Maximum number of contexts to retrieve
            temperature: Generation temperature (0.0 to 1.0)
            enable_fallback: Whether to use fallback LLM when no contexts found
            
        Returns:
            Generated answer
        """
        try:
            # Retrieve relevant contexts
            contexts = self._retrieve_contexts(question, max_contexts)
            
            if not contexts:
                if enable_fallback:
                    # Use fallback system without knowledge base context
                    fallback_prompt = """
                    You are a helpful AI assistant. Answer the user's question to the best of your ability, but be honest about the limitations of your knowledge. If the question involves dangerous, illegal, or harmful content, politely decline to answer.
                        Question: {question}
                        Answer:
                    """
                    model = GenerativeModel("gemini-2.0-flash-001")
                    response = model.generate_content(
                        fallback_prompt.format(question=question),
                        generation_config={
                            "temperature": temperature,
                            "top_p": 0.8,
                            "top_k": 40,
                            "max_output_tokens": 1024,
                        }
                    )
                    return f"I couldn't find relevant information in our knowledge base to answer your question. Here's what I can tell you based on my general knowledge: {response.text}"
                else:
                    return "I couldn't find relevant information to answer your question. Please try rephrasing or check if the knowledge base contains information about this topic."
            
            # Build prompt with improved system prompt
            if system_prompt is None:
                system_prompt = base_system_prompt

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
             system_prompt: Optional[str] = None,
             enable_fallback: bool = True) -> Tuple[str, List[Dict[str, str]]]:
        """
        Chat interface with conversation history.
        
        Args:
            question: User's question
            conversation_history: Previous conversation history
            system_prompt: Custom system prompt
            enable_fallback: Whether to use fallback when no knowledge base info found
            
        Returns:
            Tuple of (answer, updated_conversation_history)
        """
        if conversation_history is None:
            conversation_history = []
        
        # For chat, we can include recent conversation context
        chat_system_prompt = system_prompt or base_system_prompt
        
        # Generate answer
        answer = self.answer(question, chat_system_prompt, enable_fallback=enable_fallback)
        
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
        
PROJECT_ID = env_config.google_project_id
LOCATION = env_config.google_location
SERVICE_ACCOUNT_PATH = env_config.google_credentials_path
KNOWLEDGE_BASE_PATH = "knowledge_base"

faq_system = GeminiFAQSystem(
            project_id=PROJECT_ID,
            location=LOCATION,
            service_account_path=SERVICE_ACCOUNT_PATH,
            corpus_name="FAQ-Knowledge-Base",
            gcs_bucket=env_config.google_storage_bucket,
        )