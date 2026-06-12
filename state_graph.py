"""
state_graph.py
==============
LangGraph StateGraph for the multi-tenant voice sales agent.

Architecture overview
---------------------
Each inbound Deepgram STT transcript is eventually routed through this graph
instead of being forwarded raw to the LLM. The graph maintains conversation
stage across turns, enabling a React Flow UI to visualise (and later control)
which node is active in real time.

Call flow
---------
                      ┌─────────────┐
                START ──▶  greeting  │
                      └──────┬──────┘
                             │ always
                      ┌──────▼──────┐
                      │  discovery  │◀─────────────────────┐
                      └──────┬──────┘                      │
                             │ route_from_discovery()       │
                  ┌──────────┼──────────┐                  │
                  ▼          ▼          ▼                  │
           rag_lookup    objection   [END]             (resolved)
                  │          │
                  └──────────┘──── back to discovery

Node responsibilities
---------------------
greeting_node   : Emit the opening line; set stage → "discovery".
discovery_node  : Ask one qualifying question per turn; classify intent.
objection_node  : Handle price / availability / other objections.
rag_lookup_node : Call RAGFlow to ground the answer in real product data.

Conditional edges
-----------------
route_from_discovery() inspects State.current_stage (set by the LLM node)
and returns the name of the next node to execute.

Integration point (Phase 2)
----------------------------
In agent.py, after Deepgram fires an on_transcript event:
    1. Build / update the per-call State dict with the new transcript.
    2. Call: new_state = await graph.ainvoke(state, config={"tenant_id": ...})
    3. Extract new_state["messages"][-1] as the agent reply.
    4. Pass that string to session.say() → TTS pipeline.
"""

import logging
import os
import json
from typing import TypedDict, Annotated, Sequence
import operator

import httpx
from langgraph.graph import StateGraph, END

from rag_client import query_knowledge_base

logger = logging.getLogger("state-graph")


# ---------------------------------------------------------------------------
#  STATE DEFINITION
#  One State dict is maintained per active call session.
#  LangGraph merges partial updates using the reducer on `messages`.
# ---------------------------------------------------------------------------

class State(TypedDict):
    """
    Shared state object threaded through every graph node.

    messages      : Full conversation history as a list of dicts.
                    Each dict is:  {"role": "user"|"assistant", "content": str}
                    The `operator.add` reducer appends new messages rather than
                    overwriting, so nodes only need to return the delta.

    current_stage : Name of the active conversation stage.
                    Allowed values: "greeting" | "discovery" | "objection" |
                                    "rag_lookup" | "capture" | "end"
                    Nodes write this field to signal the router where to go next.

    tenant_id     : Tenant slug threaded through for RAGFlow dataset routing
                    and structured logging. Set once at call start; never mutated.

    last_user_input : The most recent Deepgram STT transcript string.
                      Populated by agent.py before each graph invocation.

    rag_context   : Retrieved passages from the last rag_lookup_node call.
                    Empty string if RAGFlow has not been queried this turn.
    """
    messages: Annotated[Sequence[dict], operator.add]
    current_stage: str
    tenant_id: str
    last_user_input: str
    rag_context: str


# ---------------------------------------------------------------------------
#  HELPER: build an assistant message dict
# ---------------------------------------------------------------------------

def _assistant_msg(content: str) -> dict:
    return {"role": "assistant", "content": content}

def _user_msg(content: str) -> dict:
    return {"role": "user", "content": content}


# ---------------------------------------------------------------------------
#  NODE: greeting_node
#  Entry point for every call. Acknowledges the pickup and transitions the
#  stage to "discovery" so the router moves there on the next turn.
#
#  In Phase 2, the actual greeting TEXT comes from TenantConfig.initial_greeting
#  and is spoken via session.say() BEFORE the graph is invoked.
#  This node therefore just records the greeting in history and sets the stage.
# ---------------------------------------------------------------------------

async def greeting_node(state: State) -> dict:
    """
    Record the greeting utterance in conversation history and advance to discovery.

    NOTE: The spoken greeting is already delivered by session.say() in agent.py
    before this graph receives its first turn. This node exists so the graph's
    message history is consistent with what the customer actually heard.
    """
    logger.info(f"[{state['tenant_id']}] greeting_node → advancing to discovery")

    greeting_text = (
        "Namaste! Mera call lene ke liye dhanyavaad. "
        "Main aapki kaise madad kar sakta hoon, yeh samajhne ke liye kuch sawaal poochna chahta hoon."
    )

    return {
        "messages": [_assistant_msg(greeting_text)],
        "current_stage": "discovery",
        "rag_context": "",
    }


# ---------------------------------------------------------------------------
#  NODE: discovery_node
#  Core qualification loop. Receives the customer's last utterance and decides:
#    - Does the customer have an objection?  → set stage = "objection"
#    - Does the question need product data?  → set stage = "rag_lookup"
#    - Is the requirement fully captured?   → set stage = "end"
#    - Otherwise, keep asking discovery Qs  → stage stays "discovery"
#
#  In Phase 2, the actual LLM call happens here using the compiled system
#  prompt from TenantConfig.build_system_prompt() + rag_context if populated.
# ---------------------------------------------------------------------------

async def discovery_node(state: State) -> dict:
    """
    LLM-powered discovery node.

    Calls Qwen via Ollama's OpenAI-compatible chat/completions endpoint to
    generate a contextual, natural Hindi/Hinglish response. The LLM also
    classifies the conversation stage for graph routing.

    Falls back to a safe generic response if the LLM call fails.
    """
    user_input = state.get("last_user_input", "").strip()
    tenant_id  = state["tenant_id"]
    messages   = state.get("messages", [])
    rag_context = state.get("rag_context", "")

    logger.info(f"[{tenant_id}] discovery_node processing via LLM: {user_input!r}")

    # ------------------------------------------------------------------
    # Build the LLM prompt
    # ------------------------------------------------------------------
    system_prompt = """You are Raj, a friendly and professional sales executive from UPM Consultancy.
You are making an outbound call to a potential customer about Tata Solar panel installations.

IMPORTANT RULES:
1. ALWAYS respond in Hindi or Hinglish (mix of Hindi and English). Never respond in pure English.
2. Keep your responses SHORT — maximum 2 sentences. This is a phone call, not an essay.
3. Be natural, warm, and conversational — like a real salesperson on the phone.
4. Listen to what the customer says and respond DIRECTLY to their question or concern.
5. If the customer asks "why are you calling" or "kaun bol raha hai", introduce yourself and explain the purpose clearly.
6. If the customer raises an objection (too expensive, not interested, busy), acknowledge it respectfully.
7. If the customer asks about pricing, specifications, or technical details, say you'll check and share.
8. Never repeat the same response twice. Always progress the conversation.
9. If the customer seems annoyed, be polite and offer to call back or send details on WhatsApp.

YOUR GOAL: Qualify the customer for a Tata Solar panel installation by understanding:
- Whether it's residential or commercial
- Their approximate monthly electricity bill
- Their roof type (RCC/tin shed)
- Their interest level

PRODUCT KNOWLEDGE:
- Tata Solar panels: 3kW to 10kW systems for homes and businesses
- Approximate pricing: ₹2-5 lakh depending on system size
- Government subsidy: Up to 40% for residential under PM Surya Ghar scheme
- EMI options available with zero down payment
- 25-year performance warranty on panels

At the END of your response, on a NEW LINE, write exactly one of these stage tags:
[STAGE:discovery] — if the conversation should continue with qualifying questions
[STAGE:objection] — if the customer raised a price/trust/competitor objection
[STAGE:rag_lookup] — if the customer asked a specific technical/pricing question you need to look up
[STAGE:end] — if the customer wants to end the call or you should wrap up"""

    if rag_context:
        system_prompt += f"\n\nRELEVANT PRODUCT DATA (use this to answer the customer's question):\n{rag_context}"

    # Build conversation history for the LLM
    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in messages:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            llm_messages.append({"role": m["role"], "content": m["content"]})
    # Add the current user input
    llm_messages.append({"role": "user", "content": user_input})

    # ------------------------------------------------------------------
    # Call Ollama via OpenAI-compatible API
    # ------------------------------------------------------------------
    ollama_base = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    ollama_model = os.getenv("LOCAL_LLM_MODEL", "qwen:latest")

    reply = ""
    next_stage = "done"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ollama_base}/chat/completions",
                json={
                    "model": ollama_model,
                    "messages": llm_messages,
                    "temperature": 0.7,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw_reply = data["choices"][0]["message"]["content"].strip()

        logger.info(f"[{tenant_id}] LLM raw response: {raw_reply!r}")

        # Parse stage tag from the response
        lines = raw_reply.split("\n")
        stage_line = ""
        reply_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[STAGE:"):
                stage_line = stripped
            else:
                reply_lines.append(line)

        reply = "\n".join(reply_lines).strip()

        # Extract stage from tag
        if "[STAGE:objection]" in stage_line:
            next_stage = "objection"
        elif "[STAGE:rag_lookup]" in stage_line:
            next_stage = "rag_lookup"
        elif "[STAGE:end]" in stage_line:
            next_stage = "end"
        else:
            next_stage = "done"  # default: continue discovery, end this invocation

        # Clean up any leftover stage tags that might be in the reply text
        for tag in ["[STAGE:discovery]", "[STAGE:objection]", "[STAGE:rag_lookup]", "[STAGE:end]"]:
            reply = reply.replace(tag, "").strip()

    except Exception as exc:
        logger.error(f"[{tenant_id}] LLM call failed, using fallback: {exc}", exc_info=True)
        # Graceful fallback — use a safe generic Hindi response
        reply = (
            "Ji sir, main UPM Consultancy se Raj bol raha hoon. "
            "Hum Tata Solar panels ki installation karte hain. "
            "Kya aap solar ke baare mein jaanna chahenge?"
        )
        next_stage = "done"

    if not reply:
        reply = "Ji sir, main samajh gaya. Aap batayein, kaise madad kar sakta hoon?"

    logger.info(f"[{tenant_id}] discovery_node → next_stage={next_stage}, reply={reply!r}")

    return {
        "messages": [
            _user_msg(state.get("last_user_input", "")),
            _assistant_msg(reply),
        ],
        "current_stage": next_stage,
    }


# ---------------------------------------------------------------------------
#  NODE: objection_node
#  Handles price, stock, inverter-brand, and DNC objections.
#  After handling, always routes back to discovery so the call can continue.
#
#  In Phase 2, the objection-handling response is LLM-generated using
#  RAGFlow-retrieved objection playbooks as grounding context.
# ---------------------------------------------------------------------------

async def objection_node(state: State) -> dict:
    """
    Generate a contextual objection-handling response and return to discovery.
    """
    user_input = state.get("last_user_input", "").lower()
    tenant_id  = state["tenant_id"]

    logger.info(f"[{tenant_id}] objection_node processing: {user_input!r}")

    # ------------------------------------------------------------------
    # STUB: generic objection response (replace with LLM call in Phase 2)
    # The LLM will select from RAGFlow-retrieved objection playbook passages.
    # ------------------------------------------------------------------
    reply = (
        "I completely understand, sir. The value here is in the brand trust, "
        "defined configuration, and approved component ecosystem. "
        "Let me share the exact configuration details that match your requirement."
    )
    # ------------------------------------------------------------------

    logger.info(f"[{tenant_id}] objection_node → returning to discovery")

    return {
        "messages": [_assistant_msg(reply)],
        "current_stage": "discovery",  # Always loop back after handling objection
    }


# ---------------------------------------------------------------------------
#  NODE: rag_lookup_node
#  Retrieves grounding context from the tenant's RAGFlow knowledge base,
#  then synthesises a response. This is the only node that calls rag_client.py.
#
#  Phase 2 wiring:
#    1. RAGFlow passages → injected as system context into LLM.
#    2. LLM generates the spoken reply grounded in real product data.
#    3. Reply stored in messages; rag_context cleared for the next turn.
# ---------------------------------------------------------------------------

async def rag_lookup_node(state: State) -> dict:
    """
    Query RAGFlow for the customer's question, then generate a grounded reply.

    Calls query_knowledge_base() from rag_client.py. When the RAGFlow server
    is live and credentials are configured, this node will return real retrieved
    passages. Until then, the stub in rag_client.py returns a safe fallback string.
    """
    user_input = state.get("last_user_input", "")
    tenant_id  = state["tenant_id"]

    logger.info(f"[{tenant_id}] rag_lookup_node querying for: {user_input!r}")

    # Call the RAGFlow async client (stub until server is live)
    rag_context = await query_knowledge_base(
        query=user_input,
        tenant_id=tenant_id,
        # api_key and dataset_id are resolved from env inside query_knowledge_base
        # when not supplied here; in Phase 2 pass them from TenantConfig explicitly:
        # api_key=tenant_cfg.ragflow_api_key,
        # dataset_id=tenant_cfg.ragflow_dataset_id,
    )

    logger.info(f"[{tenant_id}] rag_lookup_node received {len(rag_context)} chars of context")

    # ------------------------------------------------------------------
    # STUB: synthesised reply (replace with real LLM call in Phase 2)
    # In Phase 2: pass rag_context as additional system context to the LLM
    # and let it generate a natural spoken response from the retrieved passages.
    # ------------------------------------------------------------------
    if rag_context.startswith("["):
        # RAGFlow not yet configured or returned no results — graceful fallback
        reply = (
            "I want to give you accurate information, sir. "
            "Let me check with my team and confirm the exact details for you."
        )
    else:
        reply = f"Based on our product catalog: {rag_context[:200]}..."
    # ------------------------------------------------------------------

    logger.info(f"[{tenant_id}] rag_lookup_node → returning to discovery")

    return {
        "messages": [_assistant_msg(reply)],
        "current_stage": "discovery",   # Return to discovery after answering
        "rag_context": rag_context,     # Store for potential multi-turn context
    }


# ---------------------------------------------------------------------------
#  CONDITIONAL ROUTER
#  Reads state["current_stage"] and returns the name of the next node.
#  LangGraph uses this return value to select the outgoing edge.
# ---------------------------------------------------------------------------

def route_from_discovery(state: State) -> str:
    """
    Conditional edge function called after discovery_node completes.

    Reads the `current_stage` field written by discovery_node and returns
    the corresponding node name (or END sentinel) for LangGraph to route to.

    CRITICAL: This function must NEVER return "discovery_node" — that would
    create an infinite loop within a single ainvoke() call. The inter-turn
    conversational loop is managed externally by agent.py, which calls
    ainvoke() once per completed STT transcript.

    Returns
    -------
    str
        One of: "objection_node" | "rag_lookup_node" | END
    """
    stage = state.get("current_stage", "done")

    routing_map = {
        "objection":  "objection_node",
        "rag_lookup": "rag_lookup_node",
        "end":        END,
        "done":       END,   # Default qualifying turn — terminate this invocation
    }

    # Fallback to END for any unknown stage value (defensive — never loop)
    next_node = routing_map.get(stage, END)
    logger.debug(f"route_from_discovery: stage={stage!r} → {next_node}")
    return next_node


# ---------------------------------------------------------------------------
#  ENTRY ROUTING
# ---------------------------------------------------------------------------

def route_entry(state: State) -> str:
    """
    Determine the entry point of the graph based on the state.
    If the greeting has already been added to the messages list,
    bypass greeting_node and go straight to discovery_node.
    """
    if state.get("messages") and len(state["messages"]) > 0:
        return "discovery_node"
    return "greeting_node"


# ---------------------------------------------------------------------------
#  GRAPH ASSEMBLY
# ---------------------------------------------------------------------------

def build_graph() -> "CompiledGraph":
    """
    Assemble, add edges, and compile the LangGraph StateGraph.

    Returns the compiled graph object ready for .invoke() / .ainvoke() calls.

    Graph topology
    --------------
    START → greeting_node → discovery_node
                                  │
                    route_from_discovery() ──→ objection_node ──→ discovery_node
                                  │       ──→ rag_lookup_node ──→ discovery_node
                                  │       ──→ END
    """
    builder = StateGraph(State)

    # --- Register nodes ---
    builder.add_node("greeting_node",   greeting_node)
    builder.add_node("discovery_node",  discovery_node)
    builder.add_node("objection_node",  objection_node)
    builder.add_node("rag_lookup_node", rag_lookup_node)

    # --- Entry point ---
    builder.set_conditional_entry_point(
        route_entry,
        {
            "greeting_node": "greeting_node",
            "discovery_node": "discovery_node",
        }
    )

    # --- Edges ---
    # After greeting, always move to discovery
    builder.add_edge("greeting_node", "discovery_node")

    # discovery_node's output stage drives conditional routing.
    # NEVER add "discovery_node" → "discovery_node" here — that causes
    # GraphRecursionError. Each ainvoke() call processes exactly ONE turn.
    builder.add_conditional_edges(
        source="discovery_node",
        path=route_from_discovery,
        path_map={
            "objection_node":  "objection_node",
            "rag_lookup_node": "rag_lookup_node",
            END:               END,
        },
    )

    # After objection is handled → END (agent.py re-invokes on next transcript)
    builder.add_edge("objection_node", END)

    # After RAG lookup → END (agent.py re-invokes on next transcript)
    builder.add_edge("rag_lookup_node", END)

    compiled = builder.compile()
    logger.info("StateGraph compiled successfully.")
    return compiled


# ---------------------------------------------------------------------------
#  MODULE-LEVEL COMPILED GRAPH INSTANCE
#  Import this in agent.py:
#      from state_graph import sales_graph
#  Then invoke per turn:
#      new_state = await sales_graph.ainvoke(current_state)
# ---------------------------------------------------------------------------

sales_graph = build_graph()
