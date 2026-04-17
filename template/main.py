import uvicorn
from agent.core import settings
from agent.root_agent import a2a_app

if __name__ == "__main__":
    uvicorn.run(a2a_app, host="0.0.0.0", port=settings.PORT)
