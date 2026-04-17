import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from agent.core.schema_contract import get_input_schema_model

logger = logging.getLogger(__name__)

def install_schema_validation_middleware(app: FastAPI):
    """
    Installs a middleware that validates incoming JSON-RPC 2.0 requests
    against the InputSchemaModel.
    """
    
    @app.middleware("http")
    async def validate_rpc_payload(request: Request, call_next):
        if request.method != "POST" or request.url.path != "/":
            return await call_next(request)

        try:
            # Clone body to allow reading it multiple times
            body = await request.json()
            
            # ADK A2A RPC calls have a 'params' field containing the agent input
            if "params" in body and isinstance(body["params"], dict):
                # We validate the actual application payload inside the RPC params
                input_model = get_input_schema_model()
                input_model.model_validate(body["params"])
                
        except (ValueError, ValidationError) as exc:
            logger.warning("Schema validation failed for A2A request: %s", str(exc))
            # Return a standard JSON-RPC 2.0 error response
            request_id = body.get("id") if isinstance(body, dict) else None
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: " + str(exc),
                    },
                    "id": request_id
                }
            )
        except Exception as exc:
            logger.error("Unexpected error in schema validation middleware: %s", str(exc))
            
        return await call_next(request)
