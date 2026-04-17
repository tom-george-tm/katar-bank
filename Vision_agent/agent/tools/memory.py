import logging
from agent.exceptions.base import ToolConfigurationException

logger = logging.getLogger(__name__)

def get_memory_tools(memory_service) -> list:
    """
    Returns ADK's built-in memory tools if a memory service is provided.
    Enables the agent to query long-term knowledge from past conversations.
    """
    if memory_service is None:
        return []

    try:
        from google.adk.tools.load_memory import load_memory
        return [load_memory]
    except ImportError as exc:
        logger.error("Failed to import load_memory tool while memory is enabled.")
        raise ToolConfigurationException(
            "google.adk.tools.load_memory could not be imported. Ensure ADK is properly installed."
        ) from exc
