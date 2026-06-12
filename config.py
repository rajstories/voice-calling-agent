import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# =========================================================================================
#  ⚙️  MULTI-TENANT AGENT CONFIGURATION
#  Static system prompts and pricing tables have been removed.
#  Per-tenant persona, knowledge, and SIP credentials are now injected at runtime
#  via the TenantConfig dataclass (populated from room/job metadata or a future DB call).
#
#  Global constants below represent server-level defaults and hardware bindings that
#  are shared across ALL tenants running on this agent worker instance.
# =========================================================================================


# -----------------------------------------------------------------------------------------
#  SECTION 1: TENANT RUNTIME CONFIG (injected per call)
# -----------------------------------------------------------------------------------------

@dataclass
class TenantConfig:
    """
    Holds all per-tenant runtime configuration for a single agent session.

    Populated from LiveKit room/job metadata (JSON) at call start.
    In a future DB-backed flow, this will be hydrated from a Postgres/Supabase
    tenants table keyed on tenant_id.

    Fields
    ------
    tenant_id       : Unique slug for the business (e.g. "upm-consultancy").
    company_name    : Display name injected into the base system prompt.
    agent_name      : The persona name the agent introduces itself with.
    sip_trunk_id    : LiveKit SIP outbound trunk ID for this tenant's carrier account.
    ragflow_api_key : RAGFlow project API key for this tenant's knowledge base.
    ragflow_dataset_id : RAGFlow dataset/collection ID to query against.
    initial_greeting : First spoken line sent directly to TTS (bypasses LLM).
    fallback_greeting : Greeting used for inbound/room-already-joined scenarios.
    base_system_prompt : Core behavioral instructions without embedded knowledge.
                         Keep this short — factual knowledge comes from RAGFlow.
    default_transfer_number : Fallback SIP transfer target for this tenant.
    tts_provider    : Override TTS provider for this tenant (e.g. "sarvam", "elevenlabs").
    tts_voice       : Override TTS voice ID for this tenant.
    llm_provider    : Override LLM provider for this tenant (e.g. "gemini", "local-ollama").
    language        : BCP-47 language tag for STT (e.g. "hi", "en-IN").
    """
    tenant_id: str
    company_name: str
    agent_name: str

    # Telephony
    sip_trunk_id: str
    default_transfer_number: Optional[str] = None

    # RAGFlow integration
    ragflow_api_key: Optional[str] = None
    ragflow_dataset_id: Optional[str] = None

    # Dialogue
    initial_greeting: str = ""
    fallback_greeting: str = ""

    # Base system prompt — intentionally lean.
    # Product facts, pricing, objection playbooks live in RAGFlow, NOT here.
    base_system_prompt: str = (
        "You are a helpful, professional sales assistant. "
        "Always use the rag_lookup tool to retrieve product information, pricing, "
        "and company policy before answering any customer question about products or pricing. "
        "Keep responses concise — no more than 2 sentences per turn. "
        "Acknowledge before answering: e.g. 'Sure sir,' / 'Absolutely.' "
        "Never commit to stock availability, exact dispatch dates, or discounts "
        "without explicit confirmation from a human team member."
    )

    # Per-tenant model/voice overrides (fall back to global defaults if None)
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    llm_provider: Optional[str] = None

    # STT language for this tenant's callers
    language: str = "hi"

    def build_system_prompt(self) -> str:
        """
        Constructs the final LLM system prompt for this tenant.
        Injects identity fields into the base prompt so the agent knows who it is.
        All factual/product knowledge is retrieved at runtime via RAGFlow — not embedded here.
        """
        identity_header = (
            f"# IDENTITY\n"
            f"You are {self.agent_name}, a sales agent at {self.company_name}.\n\n"
        )
        return identity_header + self.base_system_prompt


def build_tenant_config_from_metadata(metadata: dict) -> TenantConfig:
    """
    Factory: construct a TenantConfig from a parsed LiveKit room/job metadata dict.
    Falls back to .env values for any field not present in metadata so that the
    existing single-tenant workflow continues to function without changes.

    Priority order: metadata dict → .env → hardcoded default.
    """
    return TenantConfig(
        tenant_id=metadata.get("tenant_id", os.getenv("DEFAULT_TENANT_ID", "default")),
        company_name=metadata.get("company_name", os.getenv("DEFAULT_COMPANY_NAME", "Our Company")),
        agent_name=metadata.get("agent_name", os.getenv("DEFAULT_AGENT_NAME", "Alex")),
        sip_trunk_id=metadata.get("sip_trunk_id", os.getenv("VOBIZ_SIP_TRUNK_ID", "")),
        default_transfer_number=metadata.get(
            "default_transfer_number", os.getenv("DEFAULT_TRANSFER_NUMBER")
        ),
        ragflow_api_key=metadata.get("ragflow_api_key", os.getenv("RAGFLOW_API_KEY")),
        ragflow_dataset_id=metadata.get("ragflow_dataset_id", os.getenv("RAGFLOW_DATASET_ID")),
        initial_greeting=metadata.get("initial_greeting", os.getenv("DEFAULT_INITIAL_GREETING", "")),
        fallback_greeting=metadata.get("fallback_greeting", os.getenv("DEFAULT_FALLBACK_GREETING", "")),
        base_system_prompt=metadata.get("base_system_prompt", ""),
        tts_provider=metadata.get("tts_provider") or metadata.get("model_provider"),
        tts_voice=metadata.get("voice_id"),
        llm_provider=metadata.get("llm_provider") or metadata.get("model_provider"),
        language=metadata.get("language", os.getenv("STT_LANGUAGE", "hi")),
    )


# -----------------------------------------------------------------------------------------
#  SECTION 2: STT (SPEECH-TO-TEXT) — SERVER-LEVEL DEFAULTS
#  These apply when a tenant does not override the language field.
# -----------------------------------------------------------------------------------------

STT_PROVIDER = "deepgram"
STT_MODEL = "nova-2"         # nova-2: best support for Hindi + Hinglish code-switching
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "hi")
#   "hi" → Hindi-first; handles Hinglish naturally.
#   Do NOT set "en" for Hindi callers — it drops Devanagari words entirely.


# -----------------------------------------------------------------------------------------
#  SECTION 3: TTS (TEXT-TO-SPEECH) — SERVER-LEVEL DEFAULTS
#  Tenant overrides via TenantConfig.tts_provider / tts_voice take precedence.
# -----------------------------------------------------------------------------------------

DEFAULT_TTS_PROVIDER = os.getenv("TTS_PROVIDER", "sarvam")
DEFAULT_TTS_VOICE = os.getenv("TTS_VOICE", "shubh")

# Sarvam AI — native Indian-accent TTS, reads Devanagari script cleanly
SARVAM_TTS_MODEL = "bulbul:v3"
SARVAM_TTS_VOICE = "shubh"
SARVAM_TTS_LANGUAGE = "hi-IN"

# ElevenLabs — multilingual, ultra-low-latency
ELEVENLABS_MODEL = "eleven_flash_v2"
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_TTS_VOICE", "hpp4J3VqNfWAUOO0d1Us")

# Cartesia
CARTESIA_MODEL = "sonic-2"
CARTESIA_VOICE = os.getenv("CARTESIA_TTS_VOICE", "f786b574-daa5-4673-aa0c-cbe3e8534c02")

# Local open-source TTS (Kokoro-82M via OpenAI-compatible server)
# Spin up: https://github.com/remsky/Kokoro-FastAPI
LOCAL_TTS_BASE_URL = os.getenv("LOCAL_TTS_BASE_URL", "http://localhost:8888/v1")
LOCAL_TTS_VOICE = os.getenv("LOCAL_TTS_VOICE", "af_bella")


# -----------------------------------------------------------------------------------------
#  SECTION 4: LLM — SERVER-LEVEL DEFAULTS
#  Tenant overrides via TenantConfig.llm_provider take precedence at session build time.
# -----------------------------------------------------------------------------------------

DEFAULT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # OpenAI fallback

# Groq
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

# Local Ollama (fully self-hosted, zero token cost)
# Run: `ollama pull llama3.1:8b && ollama serve`
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")


# -----------------------------------------------------------------------------------------
#  SECTION 5: TELEPHONY — SERVER-LEVEL DEFAULTS
#  SIP trunk and transfer target fall back to .env when not supplied by tenant metadata.
# -----------------------------------------------------------------------------------------

# Read by agent.py as a last-resort fallback if TenantConfig is not fully populated.
SIP_TRUNK_ID = os.getenv("VOBIZ_SIP_TRUNK_ID", "")
SIP_DOMAIN = os.getenv("VOBIZ_SIP_DOMAIN", "")
DEFAULT_TRANSFER_NUMBER = os.getenv("DEFAULT_TRANSFER_NUMBER")
