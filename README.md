# Travel agent

![Connect, Remember, Personalize: Building AI Agents with ADK and Memory Bank](images/title.png)

A Google ADK trip-planning agent. It asks for the missing trip details, writes an itinerary and food plan, then saves a cartoon poster as a session artifact.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "google-adk[mcp]>=1.18" "google-cloud-aiplatform[agent-engines]>=1.148.1,<2"
cp .env.example .env
```

Put a Gemini API key in `.env`:

```
GOOGLE_API_KEY=your-key
```

## Run

From this directory:

```bash
adk web
```

Open the ADK Web UI and pick `travel_agent`. The User ID field is `user` unless you change it.

## What the agent does

`travel_agent/agent.py` is an `LlmAgent` named `hotel_agent` on `gemini-2.5-flash`.

1. It asks one question at a time until it knows the destination, dates, number of people, and travel style.
2. It writes the plan in the language the guest is using: a day-by-day itinerary, then food recommendations.
3. After both parts exist, it calls `generate_trip_image` once. That tool draws a cartoon poster with `gemini-2.5-flash-image` and stores it as an artifact named `trip_cartoon_<hash>.png`.

`before_model_modifier` puts uploaded images and the generated poster back into the model request so the agent can see them.

## Memory

Each turn ends in `save_to_memory`, which copies the session into the memory service that `adk web` provides. `PreloadMemoryTool` searches that memory before the model answers.

With the default local setup that service is in-memory:

- Memories are keyed by `(app_name, user_id)`. A new session for the same user can see memories saved from older sessions in this process.
- Search is keyword overlap, up to 10 matches. A greeting with no shared words does not retrieve a saved fact.
- The store is empty again when the `adk web` process stops.

Chat history itself stays in `travel_agent/.adk/session.db` (tables `sessions` and `events`). That file is the session log, not the memory store.

## Memory Bank

`memory_bank` talks to a Vertex AI Memory Bank. It is separate from the in-memory store used by a plain `adk web` run. Set `PROJECT_ID`, `LOCATION`, and `AGENT_ENGINE_ID` in `.env`, then:

```bash
python -m memory_bank create
python -m memory_bank add --user-id user --fact "Guest is traveling with a dog named Oreo."
python -m memory_bank list --user-id user
```

`create` prints the id to put in `AGENT_ENGINE_ID`. Topics used when the bank is created are `stay_preference` and `trip_context`. Scope is `app_name=travel_agent` plus `user_id`.

`memory_bank_codelab.ipynb` walks through the same steps cell by cell, and also creates a bank with a structured profile schema.

## Run the agent with Memory Bank

Point `adk web` at the bank so `save_to_memory` and `PreloadMemoryTool` use it instead of the in-memory store. The agent code does not change.

`.env` needs the bank id and the project for the memory service:

```
GOOGLE_API_KEY=your-key
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
AGENT_ENGINE_ID=your-engine-id
```

Sign in once with Application Default Credentials, then start the Web UI:

```bash
gcloud auth application-default login
set -a; source .env; set +a
export AGENT_ENGINE_ID=7301933960752267264
adk web --memory_service_uri="agentengine://${AGENT_ENGINE_ID}"
```

`export AGENT_ENGINE_ID=...` sets the bank id for this terminal, so it works even if `.env` doesn't have it yet. Replace the number with your own bank id.

Pick `travel_agent` and keep the User ID as `user`, so the scope matches what the CLI and the notebook write.

To check that it works:

1. In one session, say something that fits a topic, for example "I'd like a non-smoking room and I'm bringing my dog."
2. Wait a few seconds, then run `python -m memory_bank list --user-id user`. The new memory should be listed.
3. Start a new session and ask for a hotel. The agent should mention the non-smoking room and the dog.

If you see `RefreshError: invalid_grant`, run `gcloud auth application-default login` again.
