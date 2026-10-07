
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _require(name: str) -> str:
    _load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name} in .env first")
    return value


def memory_bank_name() -> str:
    """Return the Memory Bank resource name from AGENT_ENGINE_ID."""
    raw = _require("AGENT_ENGINE_ID")
    if raw.startswith("projects/"):
        return raw
    project = _require("PROJECT_ID")
    location = os.environ.get("LOCATION", "us-central1").strip() or "us-central1"
    return f"projects/{project}/locations/{location}/reasoningEngines/{raw}"


def get_client():
    _load_dotenv()
    try:
        import vertexai
    except ImportError as exc:
        raise RuntimeError(
            "The vertexai package is not installed. Install it with: "
            "pip install 'google-cloud-aiplatform[agent-engines]>=1.148.1,<2'"
        ) from exc

    return vertexai.Client(
        project=_require("PROJECT_ID"),
        location=os.environ.get("LOCATION", "us-central1").strip() or "us-central1",
    )


def travel_memory_topics():
    """Topics Memory Bank uses to extract hotel-guest memories."""
    import vertexai

    types = vertexai.types
    MemoryTopic = types.MemoryBankCustomizationConfigMemoryTopic
    CustomMemoryTopic = types.MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic

    return [
        MemoryTopic(
            custom_memory_topic=CustomMemoryTopic(
                label="stay_preference",
                description="""Extract the guest's hotel and room preferences. Include:
                - Room type (single, double, suite, connecting rooms)
                - Bed preference (king, twin, extra bed)
                - Smoking or non-smoking
                - Pets (bringing a pet, type, size)
                - View, floor, and quiet-room requests
                - Amenities (pool, gym, breakfast, kitchen, parking, wifi)
                - Budget and hotel style (boutique, resort, business, budget)
                - Location (near transit, beach, old town)

                Example: "Guest wants a non-smoking room and can bring a dog."
                Example: "Guest prefers a quiet high floor and breakfast included."
                """,
            )
        ),
        MemoryTopic(
            custom_memory_topic=CustomMemoryTopic(
                label="trip_context",
                description="""Extract the guest's trip context. Include:
                - Destination city or area
                - Travel dates and number of nights
                - Who is traveling (solo, couple, family, ages of children)
                - Pets traveling along
                - Purpose (leisure, business, honeymoon)
                - Accessibility or dietary needs that affect the hotel
                - Instructions the guest asked the assistant to remember

                Example: "Guest is traveling to Chiang Mai with a golden retriever named Max."
                Example: "Guest needs 3 nights near the old town for a family with two children."
                """,
            )
        ),
    ]


def create_memory_bank(display_name: str = "travel-agent-memory") -> str:
    """Create the travel agent's Memory Bank and return its resource name.

    Put the last segment of the name in AGENT_ENGINE_ID in .env.
    """
    import vertexai

    client = get_client()
    engine = client.agent_engines.create(
        config={
            "display_name": display_name,
            "context_spec": {
                "memory_bank_config": {
                    "customization_configs": [
                        vertexai.types.MemoryBankCustomizationConfig(
                            memory_topics=travel_memory_topics(),
                        )
                    ],
                }
            },
        },
    )
    return engine.api_resource.name


def _scope(user_id: str, app_name: str) -> dict[str, str]:
    # Must match the scope the agent uses when searching memory: app_name and user_id.
    return {"app_name": app_name, "user_id": user_id}


def list_memories(user_id: str | None = None, app_name: str = "travel_agent") -> list:
    """List every memory, or only one user's scope.

    With a user_id, use RetrieveMemories because every scope key must match.
    Without a user_id, use ListMemories across the whole Memory Bank.
    """
    client = get_client()
    name = memory_bank_name()
    if user_id:
        pager = client.agent_engines.memories.retrieve(
            name=name,
            scope=_scope(user_id, app_name),
        )
        return list(pager)

    return list(client.agent_engines.memories.list(name=name))


def custom_add(fact: str, user_id: str, app_name: str = "travel_agent"):
    """Add a hand-written memory, without extracting it from a conversation or merging it with an existing one."""
    text = fact.strip()
    if not text:
        raise ValueError("fact must not be empty")

    client = get_client()
    return client.agent_engines.memories.create(
        name=memory_bank_name(),
        fact=text,
        scope=_scope(user_id, app_name),
        config={"wait_for_completion": True},
    )


def memory_fact(item) -> str:
    memory = getattr(item, "memory", None) or item
    response = getattr(memory, "response", None)
    if response is not None:
        memory = response
    fact = getattr(memory, "fact", None)
    return fact if fact else str(item)


def memory_resource_name(item) -> str | None:
    memory = getattr(item, "memory", None) or item
    response = getattr(memory, "response", None)
    if response is not None:
        memory = response
    return getattr(memory, "name", None)
