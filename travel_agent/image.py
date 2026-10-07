"""Draw a cartoon trip poster and save it as a session artifact."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google.genai.client import Client

_IMAGE_MODEL = "gemini-2.5-flash-image"


def _load_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if key:
        return key
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "GOOGLE_API_KEY" and value.strip():
                os.environ["GOOGLE_API_KEY"] = value.strip()
                return value.strip()
    raise RuntimeError("Set GOOGLE_API_KEY in .env first")


async def generate_trip_image(
    destination: str,
    trip_summary: str,
    tool_context: ToolContext,
) -> dict:
    """Draw a cartoon poster of the planned trip and save it as an artifact.

    Call this after the flight and hotel plan is ready so the guest can see the picture.

    Args:
        destination: Main city or place of the trip.
        trip_summary: Short plan with dates, flight, hotel, and what the guest will do.
    """
    place = destination.strip()
    summary = trip_summary.strip()
    if not place or not summary:
        return {"error": "destination and trip_summary are required"}

    prompt = (
        "A colorful cartoon travel poster. Cute illustrated style, bold outlines, "
        "bright flat colors, no photorealism, no readable text, no watermark. "
        f"Destination: {place}. Scene: {summary}."
    )
    client = Client(api_key=_load_api_key()).aio
    response = await client.models.generate_content(
        model=_IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )

    image_part = None
    for candidate in response.candidates or []:
        content = candidate.content
        if content is None:
            continue
        for part in content.parts or []:
            blob = part.inline_data
            if blob is not None and blob.data and blob.mime_type:
                image_part = types.Part.from_bytes(
                    data=blob.data,
                    mime_type=blob.mime_type,
                )
                break
        if image_part is not None:
            break

    if image_part is None:
        return {"error": "image generation failed"}

    image_bytes = image_part.inline_data.data or b""
    content_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
    artifact_id = f"trip_cartoon_{content_hash}.png"
    await tool_context.save_artifact(filename=artifact_id, artifact=image_part)
    return {
        "status": "sent",
        "tool_response_artifact_id": artifact_id,
    }
