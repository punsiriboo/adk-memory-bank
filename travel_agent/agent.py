from google.adk.agents import LlmAgent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

from .image import generate_trip_image
from .model_callbacks import before_model_modifier

async def save_to_memory(callback_context):
    ctx = callback_context._invocation_context
    await ctx.memory_service.add_session_to_memory(ctx.session)


root_agent = LlmAgent(
    name="hotel_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a trip planning assistant. Use what you remember about the"
        " guest. Do not jump straight into a plan.\n"
        "If you still do not know the destination, travel dates, number of"
        " people, or travel style, ask one question at a time.\n"
        "Once you have enough to plan the trip, write the plan in the language"
        " the guest is using, and include all three parts:\n"
        "1. An itinerary split by day and time of day (morning, afternoon,"
        " evening), with places and what to do.\n"
        "2. Food recommendations for each meal or neighborhood: what to eat"
        " and why it fits this trip.\n"
        "3. Only after the plan includes both the itinerary and the food, call"
        " generate_trip_image once. Put the itinerary and the food into"
        " trip_summary so a cartoon poster is saved as an artifact the guest"
        " can see.\n"
        "Do not create the image before the plan has both an itinerary and"
        " food."
    ),
    tools=[PreloadMemoryTool(), generate_trip_image],
    before_model_callback=before_model_modifier,
    after_agent_callback=save_to_memory,
)