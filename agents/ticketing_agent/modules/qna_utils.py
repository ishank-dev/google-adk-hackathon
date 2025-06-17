# agents/ticketing_agent/modules/qna_utils.py
from typing import Dict
import uuid
from datetime import datetime

from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter

from agents.multi_tool_agent_gemini.rag_kb_gemini import faq_system


RELEVANCE_PROMPT = """
You are an expert content curator for a knowledge base. Your task is to determine if the given content is relevant and valuable for a company's internal knowledge base.

Consider the following criteria:
1. **Informational Value**: Does it contain useful information for employees?
2. **Relevance**: Is it related to work, processes, tools, or company knowledge?
3. **Completeness**: Is the information complete enough to be useful?
4. **Clarity**: Is the content clear and understandable?
5. **Appropriateness**: Is it appropriate for a professional knowledge base?

Content to evaluate:
```
{content}
```

Proposed title: {title}
Proposed category: {category}

Respond with a JSON object containing:
- "relevant": true/false
- "score": a number between 0-100 (higher = more relevant)
- "reason": a brief explanation of your decision
- "suggested_title": an improved title if needed
- "suggested_category": an improved category if needed

Example response:
{{"relevant": true, "score": 85, "reason": "This content provides valuable process documentation that will help team members understand the deployment workflow.", "suggested_title": "Deployment Process Guide", "suggested_category": "processes"}}
"""

RELEVANCE_THRESHOLD = 60  # Minimum score to automatically accept content


async def check_content_relevance(content: str, title: str | None = None, category: str | None = None) -> Dict:
    """
    Use LLM to check if content is relevant for the knowledge base.
    """
    try:
        prompt = RELEVANCE_PROMPT.format(
            content=content,
            title=title or "No title provided",
            category=category or "No category provided"
        )

        response = faq_system.llm(prompt, temperature=0.3)

        import json
        try:
            result = json.loads(response)
            return {
                "relevant": result.get("relevant", False),
                "score": result.get("score", 0),
                "reason": result.get("reason", "No reason provided"),
                "suggested_title": result.get("suggested_title", title),
                "suggested_category": result.get("suggested_category", category)
            }
        except json.JSONDecodeError:
            # Fallback: simple keyword-based relevance check
            content_lower = content.lower()
            keywords = ["process", "guide", "documentation", "procedure", "workflow", 
                       "meeting", "notes", "decision", "policy", "tool", "how to"]
            
            score = sum(10 for keyword in keywords if keyword in content_lower)
            score = min(score, 100)  # Cap at 100
            
            return {
                "relevant": score >= RELEVANCE_THRESHOLD,
                "score": score,
                "reason": f"Keyword-based analysis (found {score//10} relevant terms)",
                "suggested_title": title,
                "suggested_category": category
            }
            
    except Exception as e:
        return {
            "relevant": False,
            "score": 0,
            "reason": f"Error during relevance check: {str(e)}",
            "suggested_title": title,
            "suggested_category": category
        }


async def add_document_to_vectorstore(content: str, title: str, category: str, user_id: str, 
                              context_info: str | None = None, similarity_threshold: float = 0.85,
                              enable_semantic_dedup: bool = True) -> Dict:
    """
    Add a document to the Gemini RAG system.
    """
    try:
        timestamp = datetime.now().isoformat()
        doc_id = str(uuid.uuid4())
        
        metadata = {
            "doc_type": category,
            "title": title,
            "user_id": user_id,
            "timestamp": timestamp,
            "document_id": doc_id,
            "source": "slack_command",
            "context_info": context_info or "standalone_message"
        }
        
        # Use the new add_document method with semantic deduplication
        result = await faq_system.add_document(
            content=content,
            title=title,
            doc_type=category,
            metadata=metadata,
            chunk_size=1000,
            chunk_overlap=200,
            similarity_threshold=similarity_threshold,
            enable_semantic_dedup=enable_semantic_dedup
        )
        
        assert isinstance(result, dict), "Expected result to be a dictionary"
        
        if result["status"] == "success":
            return {
                "status": "success",
                "chunks_added": 1,  # RAG handles chunking internally
                "document_id": doc_id,
                "hash": result["hash"],
                "gcs_path": result["gcs_path"]
            }
        elif result["status"] == "skipped":
            return {
                "status": "skipped",
                "reason": result["reason"],
                "existing_file": result.get("existing_file"),
                "similarity_info": result.get("similarity_info"),
                "document_id": doc_id
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "Unknown error occurred")
            }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def add_to_document(
    content: str,
    title: str | None = None,
    category: str | None = None,
    force_add: bool = False,
    user_id: str | None = None,
    context_info: str | None = None,
    similarity_threshold: float = 0.85,
    enable_semantic_dedup: bool = True
) -> Dict:
    """
    Main function to add content to the knowledge base with relevance checking.
    """
    try:
        if not title:
            title = f"Document added by {user_id or 'unknown'} on {datetime.now().strftime('%Y-%m-%d')}"
        
        if not category:
            category = "general"
        
        if not force_add:
            relevance_result = await check_content_relevance(content, title, category)
            
            if not relevance_result["relevant"] or relevance_result["score"] < RELEVANCE_THRESHOLD:
                return {
                    "status": "rejected",
                    "reason": relevance_result["reason"],
                    "relevance_score": relevance_result["score"],
                    "suggested_title": relevance_result["suggested_title"],
                    "suggested_category": relevance_result["suggested_category"]
                }
            
            title = relevance_result["suggested_title"] or title
            category = relevance_result["suggested_category"] or category
            relevance_score = relevance_result["score"]
        else:
            relevance_score = "Forced (skipped check)"
        
        add_result = await add_document_to_vectorstore(
            content, title, category, user_id or 'unknown_user', context_info,
            similarity_threshold, enable_semantic_dedup
        )
        
        if add_result["status"] == "success":
            return {
                "status": "success",
                "title": title,
                "category": category,
                "relevance_score": relevance_score,
                "chunks_added": add_result["chunks_added"],
                "document_id": add_result["document_id"],
                "hash": add_result.get("hash"),
                "gcs_path": add_result.get("gcs_path")
            }
        elif add_result["status"] == "skipped":
            return {
                "status": "skipped",
                "reason": add_result["reason"],
                "title": title,
                "category": category,
                "relevance_score": relevance_score,
                "existing_file": add_result.get("existing_file"),
                "similarity_info": add_result.get("similarity_info")
            }
        else:
            return {
                "status": "error",
                "error": add_result["error"]
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def get_document_stats() -> Dict:
    """
    Get statistics about the documents in the RAG corpus.
    """
    try:
        corpus_info = faq_system.get_corpus_info()
        
        if "error" in corpus_info:
            return {
                "error": corpus_info["error"]
            }
        
        # For more detailed stats, we could enhance this by parsing file metadata
        return {
            "total_documents": corpus_info["total_files"],
            "corpus_name": corpus_info["corpus_name"],
            "file_names": corpus_info["file_names"][:10],  # Show first 10 files
            "total_file_count": len(corpus_info["file_names"])
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }


def search_documents(query: str, max_results: int = 5) -> Dict:
    """
    Search documents in the knowledge base.
    """
    try:
        answer = faq_system.answer(query, max_contexts=max_results)
        return {
            "status": "success",
            "query": query,
            "answer": answer
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def clear_knowledge_base() -> Dict:
    """
    Clear all documents from the knowledge base (use with caution!).
    """
    try:
        stats = faq_system.clear_corpus_files()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }