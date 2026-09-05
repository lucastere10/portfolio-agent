"""Google ADK LlmAgent definition for the portfolio conversational agent."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool

from src.adk.instruction import dynamic_instruction
from src.providers.contract import generation_to_genai_config
from src.providers.factory import build_routing_llm
from src.providers.registry import GENERATION
from src.tools.portfolio_tools import get_portfolio_item

AGENT_NAME = "portfolio_agent"


def create_portfolio_agent() -> LlmAgent:
    """Build the root ADK agent with tools and dynamic instructions."""
    return LlmAgent(
        name=AGENT_NAME,
        model=build_routing_llm(),
        description=(
            "Lucas Caldas, software engineer portfolio assistant. "
            "Answers questions about background, projects, labs, and technical experience."
        ),
        instruction=dynamic_instruction,
        tools=[
            # Retrieve-once: handler already searched / built learning paths.
            # Only allow deep-dive by id when the user asks for more detail.
            FunctionTool(get_portfolio_item),
        ],
        generate_content_config=generation_to_genai_config(GENERATION),
    )
