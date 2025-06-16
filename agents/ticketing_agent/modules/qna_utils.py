# agents/ticketing_agent/modules/qna_utils.py

import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from agents.slack_agent.utils.llm import llm
from agents.multi_tool_agent_llama.rag_kb_llm import chat, vectorstore


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
        
        response = chat(prompt, llm=llm)
        
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


def add_document_to_vectorstore(content: str, title: str, category: str, user_id: str, context_info: str | None = None) -> Dict:
    """
    Add a document to the vector database.
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
        
        document = Document(page_content=content, metadata=metadata)
        
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents([document])
        
        vectorstore.add_documents(chunks)
        
        return {
            "status": "success",
            "chunks_added": len(chunks),
            "document_id": doc_id
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
    context_info: str | None = None
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
        
        add_result = add_document_to_vectorstore(content, title, category, user_id or 'unknown_user', context_info)
        
        if add_result["status"] == "success":
            return {
                "status": "success",
                "title": title,
                "category": category,
                "relevance_score": relevance_score,
                "chunks_added": add_result["chunks_added"],
                "document_id": add_result["document_id"]
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
    Get statistics about the documents in the vector store.
    """
    try:
        collection = vectorstore._collection
        count = collection.count()
        
        if count == 0:
            return {
                "total_documents": 0,
                "document_types": {}
            }
        
        result = collection.get(include=['metadatas'])
        
        if not result or 'metadatas' not in result or not result['metadatas']:
            return {
                "total_documents": count,
                "document_types": {"unknown": count}
            }
        
        doc_types = {}
        for metadata in result['metadatas']:
            if metadata is None:
                doc_type = 'unknown'
            else:
                doc_type = metadata.get('doc_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        return {
            "total_documents": count,
            "document_types": doc_types
        }
    except Exception as e:
        return {
            "error": str(e)
        }