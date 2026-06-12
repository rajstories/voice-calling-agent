import os
import certifi

# Fix for macOS SSL Certificate errors - MUST be before other imports
os.environ['SSL_CERT_FILE'] = certifi.where()

import logging
import json
import asyncio
from dotenv import load_dotenv

from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.agents import TurnHandlingOptions
from livekit.agents.voice.turn import EndpointingOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
    elevenlabs,
    sarvam,
)
from livekit.agents import llm
from typing import Annotated, Optional

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound-agent")

import config
from config import TenantConfig, build_tenant_config_from_metadata

# ---------------------------------------------------------------------------
# Phase 2 — LangGraph import
# The compiled sales_graph is imported here so it is ready to be wired into
# the Deepgram STT transcript callback inside entrypoint().
# See the ═══ LANGGRAPH INTEGRATION HOOK ═══ comment block further below.
# ---------------------------------------------------------------------------
from state_graph import sales_graph


def _build_tts(tenant: TenantConfig):
    """
    Configure the Text-to-Speech provider for a specific tenant session.

    Priority order:
      1. tenant.tts_provider  (set from room/job metadata)
      2. TTS_PROVIDER env var
      3. config.DEFAULT_TTS_PROVIDER server default

    Local provider:
      "local-kokoro" → routes to a self-hosted Kokoro-82M FastAPI server
      (https://github.com/remsky/Kokoro-FastAPI) running at LOCAL_TTS_BASE_URL.
      Zero character cost — fully offline once the container is up.
    """
    provider = (
        tenant.tts_provider
        or os.getenv("TTS_PROVIDER", config.DEFAULT_TTS_PROVIDER)
    ).lower()
    config_voice = tenant.tts_voice

    # ------------------------------------------------------------------
    # LOCAL: Kokoro-82M (self-hosted, zero cost)
    # Exposes an OpenAI-compatible /v1/audio/speech endpoint so we can
    # reuse the livekit-plugins-openai TTS adapter with no code changes.
    # ------------------------------------------------------------------
    if provider == "local-kokoro":
        logger.info(f"[{tenant.tenant_id}] Using Local Kokoro TTS @ {config.LOCAL_TTS_BASE_URL}")
        return openai.TTS(
            base_url=config.LOCAL_TTS_BASE_URL,
            api_key="kokoro",                     # Kokoro server ignores the key; must not be empty
            model="kokoro",
            voice=config_voice or config.LOCAL_TTS_VOICE,
        )

    if provider == "cartesia":
        logger.info(f"[{tenant.tenant_id}] Using Cartesia TTS")
        model = os.getenv("CARTESIA_TTS_MODEL", config.CARTESIA_MODEL)
        voice = config_voice or os.getenv("CARTESIA_TTS_VOICE", config.CARTESIA_VOICE)
        return cartesia.TTS(model=model, voice=voice)

    if provider == "elevenlabs":
        logger.info(f"[{tenant.tenant_id}] Using ElevenLabs TTS")
        model = os.getenv("ELEVENLABS_TTS_MODEL", config.ELEVENLABS_MODEL)
        voice = config_voice or os.getenv("ELEVENLABS_TTS_VOICE", config.ELEVENLABS_VOICE)
        return elevenlabs.TTS(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            model=model,
            voice_id=voice,
        )

    if provider == "sarvam":
        logger.info(f"[{tenant.tenant_id}] Using Sarvam TTS")
        return sarvam.TTS(
            api_key=os.getenv("SARVAM_API_KEY"),
            model=os.getenv("SARVAM_TTS_MODEL", config.SARVAM_TTS_MODEL),
            speaker=config_voice or os.getenv("SARVAM_TTS_VOICE", config.SARVAM_TTS_VOICE),
            target_language_code=os.getenv("SARVAM_TTS_LANGUAGE", config.SARVAM_TTS_LANGUAGE),
        )

    if provider == "deepgram":
        logger.info(f"[{tenant.tenant_id}] Using Deepgram TTS")
        model = os.getenv("DEEPGRAM_TTS_MODEL", "aura-asteria-en")
        return deepgram.TTS(model=model)

    # Default to OpenAI
    logger.info(f"[{tenant.tenant_id}] Using OpenAI TTS (voice: {config_voice})")
    model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    voice = config_voice or os.getenv("OPENAI_TTS_VOICE", config.DEFAULT_TTS_VOICE)
    return openai.TTS(model=model, voice=voice)


def _build_llm(tenant: TenantConfig):
    """
    Configure the LLM provider for a specific tenant session.

    Priority order:
      1. tenant.llm_provider  (set from room/job metadata)
      2. LLM_PROVIDER env var
      3. config.DEFAULT_LLM_PROVIDER server default

    Local provider:
      "local-ollama" → routes to a self-hosted Ollama server running at
      LOCAL_LLM_BASE_URL (default: http://localhost:11434/v1).
      Ollama exposes an OpenAI-compatible /v1/chat/completions endpoint,
      so the livekit-plugins-openai adapter works with zero plugin changes.
      Setup: `ollama pull llama3.1:8b && ollama serve`
    """
    provider = (
        tenant.llm_provider
        or os.getenv("LLM_PROVIDER", config.DEFAULT_LLM_PROVIDER)
    ).lower()

    # ------------------------------------------------------------------
    # LOCAL: Ollama (self-hosted, zero token cost)
    # Runs Llama 3.1 / Phi-3 / Mistral locally via an OpenAI-compatible
    # endpoint. No API key required. No rate limits. No billing.
    # ------------------------------------------------------------------
    if provider == "local-ollama":
        logger.info(
            f"[{tenant.tenant_id}] Using Local Ollama LLM "
            f"@ {config.LOCAL_LLM_BASE_URL} model={config.LOCAL_LLM_MODEL}"
        )
        return openai.LLM(
            base_url=config.LOCAL_LLM_BASE_URL,
            api_key="ollama",               # Ollama ignores the key; must not be empty
            model=config.LOCAL_LLM_MODEL,
            temperature=0.7,
        )

    if provider == "gemini":
        logger.info(f"[{tenant.tenant_id}] Using Gemini LLM")
        return openai.LLM(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.getenv("GEMINI_API_KEY"),
            model="gemini-2.5-flash-lite",  # Fast, low-latency, suits real-time voice
            temperature=0.7,
        )

    if provider == "groq":
        logger.info(f"[{tenant.tenant_id}] Using Groq LLM")
        return openai.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            model=os.getenv("GROQ_MODEL", config.GROQ_MODEL),
            temperature=float(os.getenv("GROQ_TEMPERATURE", str(config.GROQ_TEMPERATURE))),
        )

    # Default to OpenAI
    logger.info(f"[{tenant.tenant_id}] Using OpenAI LLM")
    return openai.LLM(model=config.DEFAULT_LLM_MODEL)



class TransferFunctions(llm.ToolContext):
    def __init__(self, ctx: agents.JobContext, phone_number: str = None, tenant: TenantConfig = None):
        super().__init__(tools=[])
        self.ctx = ctx
        self.phone_number = phone_number
        self.tenant = tenant

    @llm.function_tool(description="Transfer the call to a human support agent or another phone number.")
    async def transfer_call(self, destination: Optional[str] = None):
        """
        Transfer the call to another phone number.

        Args:
            destination: The target phone number to transfer to (in E.164 format, e.g., +917971442049). If not specified, defaults to the administration number.
        """
        # Resolve transfer target: explicit arg → tenant default → global env default
        if destination is None:
            destination = (
                (self.tenant.default_transfer_number if self.tenant else None)
                or config.DEFAULT_TRANSFER_NUMBER
            )
            if not destination:
                return "Error: No default transfer number configured."

        # Resolve SIP domain: tenant config → global env default
        sip_domain = (self.tenant.sip_trunk_id and config.SIP_DOMAIN) or config.SIP_DOMAIN

        if "@" not in destination:
            if sip_domain:
                clean_dest = destination.replace("tel:", "").replace("sip:", "")
                destination = f"sip:{clean_dest}@{sip_domain}"
            else:
                if not destination.startswith("tel:") and not destination.startswith("sip:"):
                    destination = f"tel:{destination}"
        elif not destination.startswith("sip:"):
            destination = f"sip:{destination}"
        
        logger.info(f"Transferring call to {destination}")
        
        # Determine the participant identity
        # For outbound calls initiated by this agent, the participant identity is typically "sip_<phone_number>"
        # For inbound, we might need to find the remote participant.
        participant_identity = None
        
        # If we stored the phone number from metadata, we can construct the identity
        if self.phone_number:
            participant_identity = f"sip_{self.phone_number}"
        else:
            # Try to find a participant that is NOT the agent
            for p in self.ctx.room.remote_participants.values():
                participant_identity = p.identity
                break
        
        if not participant_identity:
            logger.error("Could not determine participant identity for transfer")
            return "Failed to transfer: could not identify the caller."

        try:
            logger.info(f"Transferring participant {participant_identity} to {destination}")
            await self.ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=self.ctx.room.name,
                    participant_identity=participant_identity,
                    transfer_to=destination,
                    play_dialtone=False
                )
            )
            return "Transfer initiated successfully."
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return f"Error executing transfer: {e}"


class OutboundAssistant(Agent):
    """
    An AI agent tailored for outbound calls.

    Receives a compiled TenantConfig so the system prompt is dynamically
    assembled from the tenant's identity fields (agent_name, company_name,
    base_system_prompt) rather than the old static config.SYSTEM_PROMPT.

    In Phase 2, this class will also hold a reference to the per-call
    LangGraph state so the LiveKit turn pipeline can consult it.
    """
    def __init__(self, tools: list, tenant: TenantConfig) -> None:
        super().__init__(
            instructions=tenant.build_system_prompt(),
            tools=tools,
        )
        self.tenant = tenant




async def entrypoint(ctx: agents.JobContext):
    """
    Main entrypoint for the agent.

    For outbound calls:
    1. Parses phone_number and all tenant config from room/job metadata.
    2. Builds a TenantConfig instance for this specific call.
    3. Connects to the LiveKit room and starts the AgentSession.
    4. Initiates the SIP call (if outbound) and speaks the initial greeting.
    """
    logger.info(f"Connecting to room: {ctx.room.name}")

    # -----------------------------------------------------------------------
    # Step 1: Parse metadata from LiveKit job and room
    #   - Job metadata is set by make_call.py / the CLI dispatch tool.
    #   - Room metadata is set by dashboard/app/api/dispatch/route.ts.
    #   - Room metadata takes precedence (it is set later and may carry richer config).
    # -----------------------------------------------------------------------
    phone_number = None
    config_dict: dict = {}

    # Job metadata (legacy / CLI dispatch)
    try:
        if ctx.job.metadata:
            data = json.loads(ctx.job.metadata)
            phone_number = data.get("phone_number")
            config_dict = data
    except Exception:
        pass

    # Room metadata (dashboard dispatch — overrides job metadata)
    try:
        if ctx.room.metadata:
            data = json.loads(ctx.room.metadata)
            if data.get("phone_number"):
                phone_number = data.get("phone_number")
            config_dict.update(data)  # Merge: room values win on collision
    except Exception:
        logger.warning("No valid JSON metadata found in Room. Using env-var defaults.")

    # -----------------------------------------------------------------------
    # Step 2: Build TenantConfig for this call
    #   All per-tenant settings (agent identity, RAGFlow creds, voice, LLM
    #   provider) are now resolved in one place from the merged metadata dict.
    # -----------------------------------------------------------------------
    tenant = build_tenant_config_from_metadata(config_dict)
    logger.info(
        f"Tenant resolved: id={tenant.tenant_id!r} "
        f"agent={tenant.agent_name!r} "
        f"llm={tenant.llm_provider or 'default'!r} "
        f"tts={tenant.tts_provider or 'default'!r}"
    )

    # -----------------------------------------------------------------------
    # Step 3: Initialise per-call graph state
    #   This dict is the Phase 2 integration point for LangGraph.
    #   See the ═══ LANGGRAPH INTEGRATION HOOK ═══ block below for details.
    # -----------------------------------------------------------------------
    call_graph_state: dict = {
        "messages":        [],
        "current_stage":   "greeting",
        "tenant_id":       tenant.tenant_id,
        "last_user_input": "",
        "rag_context":     "",
    }
    # Reference to the compiled graph — ready for Phase 2 ainvoke() calls.
    # In Phase 1, this object exists but is NOT yet called from the audio loop.
    _graph = sales_graph  # noqa: F841  (used in Phase 2 wiring below)

    # -----------------------------------------------------------------------
    # Step 4: Build model providers from TenantConfig
    # -----------------------------------------------------------------------
    stt_language = tenant.language or config.STT_LANGUAGE

    # Initialize transfer/tool functions
    fnc_ctx = TransferFunctions(ctx, phone_number, tenant)

    # ═══════════════════════════════════════════════════════════════════════
    # ═══          LANGGRAPH INTEGRATION HOOK  (Phase 2 target)           ═══
    # ═══════════════════════════════════════════════════════════════════════
    #
    # CURRENT STATE (Phase 1):
    #   LiveKit's AgentSession handles the full STT → LLM → TTS pipeline
    #   automatically. Deepgram transcripts flow directly into the raw LLM
    #   (Gemini / Groq / Ollama) via the livekit-agents turn pipeline.
    #
    # PHASE 2 WIRING PLAN:
    #   We will intercept the Deepgram transcript BEFORE it reaches the LLM
    #   by hooking into one of the following LiveKit Agents extension points:
    #
    #   OPTION A — Override Agent.on_user_turn_completed() (recommended)
    #   ────────────────────────────────────────────────────────────────────
    #   class OutboundAssistant(Agent):
    #       async def on_user_turn_completed(
    #           self,
    #           turn_ctx: ChatContext,          # contains the full chat history
    #           new_message: ChatMessage,       # the just-transcribed user utterance
    #       ) -> None:
    #
    #           # 1. Extract the plain-text transcript from the LiveKit message.
    #           transcript: str = new_message.text_content
    #
    #           # 2. Update the per-call LangGraph state with the new input.
    #           self._call_graph_state["last_user_input"] = transcript
    #
    #           # 3. Invoke the LangGraph asynchronously.
    #           #    sales_graph.ainvoke() runs the node chain for ONE turn:
    #           #      discovery_node → (route) → objection_node / rag_lookup_node
    #           new_state = await sales_graph.ainvoke(
    #               self._call_graph_state,
    #               config={"configurable": {"thread_id": self.tenant.tenant_id}}
    #           )
    #
    #           # 4. Update shared state for the next turn.
    #           self._call_graph_state = new_state
    #
    #           # 5. Extract the last assistant message produced by the active node.
    #           assistant_msgs = [
    #               m for m in new_state["messages"]
    #               if m.get("role") == "assistant"
    #           ]
    #           agent_reply: str = assistant_msgs[-1]["content"] if assistant_msgs else ""
    #
    #           # 6. Speak the reply directly via TTS, bypassing the raw LLM entirely.
    #           #    session.say() pushes the text straight to the TTS pipeline,
    #           #    so latency = (RAGFlow retrieval) + (TTS synthesis) only.
    #           if agent_reply:
    #               await session.say(agent_reply, allow_interruptions=True)
    #
    #           # 7. Suppress the default LLM generate_reply() call so the
    #           #    livekit-agents pipeline does NOT also fire its own LLM call.
    #           return   # Returning here signals LiveKit to skip default handling
    #
    #   OPTION B — Attach an on_transcript event listener to the STT stream
    #   ────────────────────────────────────────────────────────────────────
    #   @session.on("user_speech_committed")
    #   async def _on_transcript(event: SpeechEvent):
    #       transcript = event.alternatives[0].text
    #       call_graph_state["last_user_input"] = transcript
    #       new_state = await sales_graph.ainvoke(call_graph_state)
    #       call_graph_state.update(new_state)
    #       reply = [m for m in new_state["messages"] if m["role"] == "assistant"][-1]["content"]
    #       await session.say(reply)
    #
    # WHY OPTION A IS PREFERRED:
    #   on_user_turn_completed() fires AFTER VAD silence detection completes
    #   the full utterance, giving us access to the complete transcript in one
    #   shot. Option B fires on every partial/interim STT event and requires
    #   additional debouncing.
    #
    # PORTING NOTE FOR RAG CONTEXT:
    #   The rag_lookup_node in state_graph.py already calls
    #   query_knowledge_base() from rag_client.py. When the RAGFlow server
    #   is live, only the two commented-out lines in _call_ragflow_api() need
    #   to be uncommented — no graph changes required.
    # ═══════════════════════════════════════════════════════════════════════

    # Initialize the Agent Session with tenant-resolved model providers
    session = AgentSession(
        vad=silero.VAD.load(
            min_silence_duration=0.6,   # 600 ms silence → end-of-speech
            activation_threshold=0.65,  # Higher threshold ignores SIP line noise
            min_speech_duration=0.15,   # Ignore short clicks / carrier pops
            max_buffered_speech=60.0,   # Allow long sentences without cutoff
        ),
        stt=deepgram.STT(model=config.STT_MODEL, language=stt_language),
        llm=_build_llm(tenant),
        tts=_build_tts(tenant),
        turn_handling=TurnHandlingOptions(
            endpointing=EndpointingOptions(
                min_delay=0.5,  # Wait at least 500 ms after speech ends
                max_delay=6.0,  # Give up waiting for more speech after 6 s
            )
        ),
    )

    # Start the session — binds the audio pipeline to this LiveKit room
    await session.start(
        room=ctx.room,
        agent=OutboundAssistant(
            tools=list(fnc_ctx.function_tools.values()),
            tenant=tenant,
        ),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    # -----------------------------------------------------------------------
    # Step 5: Dial out (outbound calls) or greet (inbound/room-already-joined)
    # -----------------------------------------------------------------------
    should_dial = False
    if phone_number:
        user_already_here = False
        for p in ctx.room.remote_participants.values():
            if f"sip_{phone_number}" in p.identity or "sip_" in p.identity:
                user_already_here = True
                break

        if not user_already_here:
            should_dial = True
            logger.info("User not in room. Agent will initiate dial-out.")
        else:
            logger.info("User already in room (Dashboard dispatched). Generating greeting only.")

    if should_dial:
        logger.info(f"[{tenant.tenant_id}] Initiating outbound SIP call to {phone_number}...")
        try:
            # --- CONNECTING TO THE PHONE NETWORK ---
            # create_sip_participant dials the number via the Vobiz SIP trunk,
            # brings the customer into the LiveKit room, and blocks until answered.
            await ctx.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=tenant.sip_trunk_id or config.SIP_TRUNK_ID,
                    sip_call_to=phone_number,
                    participant_identity=f"sip_{phone_number}",
                    wait_until_answered=True,  # Block until the customer picks up
                )
            )
            logger.info("Call answered. Applying 2-second carrier stabilisation buffer.")
            await asyncio.sleep(2.0)
            logger.info("Buffer complete. Speaking initial greeting.")

            # Speak greeting DIRECTLY to TTS — no LLM round-trip.
            # Avoids the Gemini 400 error (empty conversation context).
            # Greeting text comes from TenantConfig so it is tenant-specific.
            greeting_text = (
                tenant.initial_greeting
                or f"Hello! This is {tenant.agent_name} from {tenant.company_name}. "
                   "Can I have two minutes of your time?"
            )
            await session.say(greeting_text, allow_interruptions=False)

        except Exception as e:
            logger.error(f"[{tenant.tenant_id}] Failed to place outbound call: {e}")
            ctx.shutdown()
    else:
        # Inbound / room-already-joined path
        logger.info(f"[{tenant.tenant_id}] Inbound call detected. Speaking fallback greeting.")
        fallback_text = (
            tenant.fallback_greeting
            or f"Hello! You've reached {tenant.agent_name} at {tenant.company_name}. "
               "How can I help you today?"
        )
        await session.say(fallback_text, allow_interruptions=False)


if __name__ == "__main__":
    # The agent name "outbound-caller" is used by the dispatch script to find this worker
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="outbound-caller", 
        )
    )
