import hashlib

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai.types import Part

_IMAGE_TOOLS = {"generate_trip_image"}


async def before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Put artifact images back into the model request, both uploads and the trip poster."""
    for content in llm_request.contents:
        if not content.parts:
            continue

        modified_parts = []
        for part in content.parts:
            if part.inline_data:
                processed_parts = await _process_inline_data_part(
                    part, callback_context
                )
            elif part.function_response:
                if part.function_response.name in _IMAGE_TOOLS:
                    processed_parts = await _process_function_response_part(
                        part, callback_context
                    )
                else:
                    processed_parts = [part]
            else:
                processed_parts = [part]
            modified_parts.extend(processed_parts)

        content.parts = modified_parts
    return None


async def _process_inline_data_part(
    part: Part, callback_context: CallbackContext
) -> list[Part]:
    """Save an uploaded image as an artifact and place a pointer before the image part."""
    artifact_id = _generate_artifact_id(part)
    if artifact_id not in await callback_context.list_artifacts():
        await callback_context.save_artifact(filename=artifact_id, artifact=part)
    return [
        Part(
            text=(
                "[User Uploaded Artifact] Below is the content of artifact ID : "
                f"{artifact_id}"
            )
        ),
        part,
    ]


def _generate_artifact_id(part: Part) -> str:
    filename = part.inline_data.display_name or "uploaded_image"
    image_data = part.inline_data.data or b""
    hash_input = filename.encode("utf-8") + image_data
    content_hash = hashlib.sha256(hash_input).hexdigest()[:16]
    mime_type = part.inline_data.mime_type or "image/png"
    extension = mime_type.split("/")[-1]
    return f"usr_upl_img_{content_hash}.{extension}"


async def _process_function_response_part(
    part: Part, callback_context: CallbackContext
) -> list[Part]:
    """Load the trip poster artifact and pass the image through to the model."""
    response = part.function_response.response or {}
    artifact_id = response.get("tool_response_artifact_id")
    if not artifact_id:
        return [part]

    artifact = await callback_context.load_artifact(filename=artifact_id)
    if artifact is None:
        return [part]

    return [
        part,
        Part(
            text=(
                "[Tool Response Artifact] Below is the content of artifact ID : "
                f"{artifact_id}"
            )
        ),
        artifact,
    ]
