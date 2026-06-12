"""
rag_client.py
=============
Async HTTP client for the RAGFlow enterprise document retrieval API.

Architecture note
-----------------
RAGFlow is a self-hosted, GPU-backed RAG engine (https://ragflow.io).
Each tenant uploads their own knowledge base (pricing books, playbooks, FAQs)
to a RAGFlow "dataset". This client queries the dataset at inference time and
returns the top-k retrieved passages, which the LLM uses as grounded context
instead of having facts baked into the system prompt.

Usage (once RAGFlow server is live)
-------------------------------------
1. Set RAGFLOW_BASE_URL in .env (e.g. http://your-server:9380)
2. Each tenant provides their ragflow_api_key and ragflow_dataset_id via
   room/job metadata (see TenantConfig in config.py).
3. Call `query_knowledge_base(query, tenant_id, api_key, dataset_id)`
   from the LangGraph rag_lookup_node (state_graph.py).

Current status: STUB — returns a dummy string so the graph compiles and runs.
Replace the _call_ragflow_api() body with the real HTTP call when the server is ready.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("rag-client")

# ---------------------------------------------------------------------------
#  Server-level defaults (override per-tenant via TenantConfig fields)
# ---------------------------------------------------------------------------

RAGFLOW_BASE_URL: str = os.getenv("RAGFLOW_BASE_URL", "http://localhost:9380")
RAGFLOW_TIMEOUT_SECONDS: float = float(os.getenv("RAGFLOW_TIMEOUT_SECONDS", "5.0"))
RAGFLOW_TOP_K: int = int(os.getenv("RAGFLOW_TOP_K", "3"))


# ---------------------------------------------------------------------------
#  Internal HTTP call (private — only called through the public interface)
# ---------------------------------------------------------------------------

async def _call_ragflow_api(
    query: str,
    api_key: str,
    dataset_id: str,
    top_k: int = RAGFLOW_TOP_K,
) -> list[dict]:
    """
    Send a retrieval request to the RAGFlow REST API and return raw result chunks.

    RAGFlow API reference (v0.12+):
      POST /api/v1/retrieval
      Headers: { Authorization: "Bearer <api_key>" }
      Body:    { "question": str, "datasets": [str], "top_k": int }
      Response: { "data": { "chunks": [ { "content": str, "score": float } ] } }

    Returns
    -------
    list[dict]
        Each dict has at minimum:  {"content": str, "score": float}
        Returns an empty list on any network or parse error.
    """
    url = f"{RAGFLOW_BASE_URL.rstrip('/')}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "question": query,
        "datasets": [dataset_id],
        "top_k": top_k,
    }

    # -----------------------------------------------------------------------
    # STUB: Return empty list until RAGFlow server is live.
    # When ready, delete the two lines below and uncomment the httpx block.
    # -----------------------------------------------------------------------
    logger.debug("[RAG STUB] Skipping real HTTP call. Returning empty chunk list.")
    return []

    # --- REAL IMPLEMENTATION (uncomment when RAGFlow server is running) ---
    # async with httpx.AsyncClient(timeout=RAGFLOW_TIMEOUT_SECONDS) as client:
    #     try:
    #         resp = await client.post(url, headers=headers, json=payload)
    #         resp.raise_for_status()
    #         data = resp.json()
    #         chunks = data.get("data", {}).get("chunks", [])
    #         logger.debug(f"[RAG] Retrieved {len(chunks)} chunks for query: {query!r}")
    #         return chunks
    #     except httpx.TimeoutException:
    #         logger.warning(f"[RAG] Timeout querying RAGFlow for: {query!r}")
    #         return []
    #     except httpx.HTTPStatusError as exc:
    #         logger.error(f"[RAG] HTTP {exc.response.status_code} from RAGFlow: {exc.response.text}")
    #         return []
    #     except Exception as exc:
    #         logger.error(f"[RAG] Unexpected error: {exc}")
    #         return []


# ---------------------------------------------------------------------------
#  Public interface — called by state_graph.py rag_lookup_node
# ---------------------------------------------------------------------------

async def query_knowledge_base(
    query: str,
    tenant_id: str,
    api_key: Optional[str] = None,
    dataset_id: Optional[str] = None,
) -> str:
    """
    Retrieve grounding context from the tenant's RAGFlow knowledge base.

    This is the function called by the LangGraph `rag_lookup_node`. It wraps
    the raw HTTP call and formats the retrieved passages into a single string
    that the LLM can directly consume as injected context.

    Parameters
    ----------
    query      : The customer's utterance or the agent's search query.
    tenant_id  : Used for structured logging / future per-tenant routing.
    api_key    : RAGFlow project API key (from TenantConfig.ragflow_api_key).
                 Falls back to RAGFLOW_API_KEY env var.
    dataset_id : RAGFlow dataset/collection ID (from TenantConfig.ragflow_dataset_id).
                 Falls back to RAGFLOW_DATASET_ID env var.

    Returns
    -------
    str
        A newline-separated block of retrieved text passages.
        Returns a safe fallback string if retrieval fails or is unconfigured,
        so the LLM can still respond gracefully without crashing.
    """
    resolved_api_key = api_key or os.getenv("RAGFLOW_API_KEY", "")
    resolved_dataset_id = dataset_id or os.getenv("RAGFLOW_DATASET_ID", "")

    # Guard: if RAGFlow is not yet configured for this tenant, return a clear
    # signal so the LLM knows to ask the customer to wait or escalate.
    if not resolved_api_key or not resolved_dataset_id:
        logger.warning(
            f"[RAG] No RAGFlow credentials configured for tenant='{tenant_id}'. "
            "Returning safe fallback."
        )
        return (
            "[Knowledge base not yet configured for this agent. "
            "Please escalate to a human team member for detailed product/pricing queries.]"
        )

    logger.info(f"[RAG] Querying knowledge base for tenant='{tenant_id}': {query!r}")

    chunks = await _call_ragflow_api(
        query=query,
        api_key=resolved_api_key,
        dataset_id=resolved_dataset_id,
    )

    if not chunks:
        logger.info(f"[RAG] No chunks returned for query: {query!r}")
        return "[No relevant information found in the knowledge base for this query.]"

    # Format chunks as a numbered list for clean LLM consumption
    formatted_passages = []
    for i, chunk in enumerate(chunks, start=1):
        content = chunk.get("content", "").strip()
        score = chunk.get("score", 0.0)
        if content:
            formatted_passages.append(f"[{i}] (relevance: {score:.2f})\n{content}")

    if not formatted_passages:
        return "[Retrieved chunks contained no usable text content.]"

    return "\n\n".join(formatted_passages)
