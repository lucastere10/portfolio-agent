"""Google ADK LlmAgent definition for the portfolio conversational agent."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from src.adk.instruction import dynamic_instruction
from src.providers.factory import resolve_model
from src.tools.portfolio_tools import (
    build_learning_path,
    get_portfolio_item,
    search_portfolio,
)

AGENT_NAME = "portfolio_agent"

def create_portfolio_agent() -> LlmAgent:
    """Build the root ADK agent with tools and dynamic instructions."""
    return LlmAgent(
        name=AGENT_NAME,
        model=resolve_model(),
        description=(
            "Lucas Caldas — software engineer portfolio assistant. "
            "Answers questions about background, projects, labs, and technical experience."
        ),
        instruction=dynamic_instruction,
        tools=[
            FunctionTool(search_portfolio),
            FunctionTool(get_portfolio_item),
            FunctionTool(build_learning_path),
        ],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.45,
            max_output_tokens=700,
        ),
    )
