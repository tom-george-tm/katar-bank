import uvicorn
from agent.core import settings
from agent.root_agent import a2a_app

if __name__ == "__main__":
    # Run the A2A Agent Server using the port and host specified in settings
    uvicorn.run(
        "agent.root_agent:a2a_app", 
        host="0.0.0.0", 
        port=settings.PORT,
        reload=True if settings.settings.get("DEBUG") else False # Optional reload if debug enabled
    )
