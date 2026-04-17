# Vision Agent

## Overview

A robust, production-ready Document AI and Gemini Vision orchestrator built on the Google Agent Development Kit (ADK) architecture. The Vision Agent automates complex document processing workflows, combining high-accuracy OCR with large language model reasoning.

The agent supports three primary pipelines:
1.  **OCR Pipeline**: Structured data extraction using Google Document AI (Forms, Tables, Layouts).
2.  **Vision Pipeline**: Semantic understanding and freeform reasoning using Gemini Vision models.
3.  **Hybrid (OCR + Vision) Pipeline**: Maximum accuracy by providing both the original document image and the extracted OCR text to Gemini for multi-modal reasoning.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd "Vision Agent"

# Install dependencies
pip install -r requirements.txt
```

## Configuration

The application uses a centralized configuration system. Copy the example environment file and update the variables:

```bash
cp .env.example .env
```

### Key Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP Project ID |
| `VERTEX_AI_LOCATION` | Region for Gemini (e.g., `us-central1`) |
| `DOCAI_LOCATION` | Region for Document AI (e.g., `us`) |
| `LLM_MODEL` | Gemini model name (e.g., `gemini-2.0-flash`) |
| `CREDENTIALS_PATH` | Path to your GCP service account JSON key |
| `DOCAI_DOCUMENT_OCR_ID` | Processor ID for Document OCR |
| `DOCAI_FORM_PARSER_ID` | Processor ID for Form Parser |
| `ENABLE_CLOUD_TRACE` | Set to `true` to export traces to Google Cloud |

## Usage

### Starting the Server

The agent is exposed via a FastAPI application:

```bash
python -m uvicorn app.main:app --reload
```

### API Endpoints

- **GET `/vision-service/v1/health`**: Health check.
- **GET `/vision-service/v1/capabilities`**: Lists supported flows and processor types.
- **POST `/vision-service/v1/documents/process`**: Main execution endpoint.
    - Supports local file uploads or GCS URIs (`gs://...`).
    - Configurable `flow_type` (`ocr_pipeline`, `vision_pipeline`, `ocr_vision_pipeline`).
    - Supports custom prompts and JSON extraction schemas.

## Directory Structure

The project follows a modular ADK-inspired layout, separating core infrastructure from application-specific business logic.

```
.
├── agent/                      # Main Agent Logic
│   ├── core/                   # Infrastructure & Foundation
│   │   ├── config.py           # Pydantic Settings & Env management
│   │   ├── otel.py             # OpenTelemetry & Tracing setup
│   │   ├── model/              # Model provider logic (Vertex AI / Model Garden)
│   │   └── state_management/   # ADK-standard state services (Firestore, Redis, etc.)
│   ├── services/               # Low-level Cloud Service Integrations
│   │   ├── docai_service.py    # Document AI client wrapper
│   │   ├── vertex_service.py   # Gemini Vision client wrapper
│   │   ├── file_source_service.py # GCS download & URI parsing
│   │   └── preprocessing_service.py # Image cleaning & PDF normalization
│   ├── tools/                  # Atomic Tools used by the Orchestrator
│   │   ├── ocr_tools.py        # Wrapper for Document AI execution
│   │   ├── vision_tools.py     # Wrapper for Gemini Vision execution
│   │   ├── storage_tools.py    # Cloud Storage utilities
│   │   └── preprocess_tools.py # Document optimization tool
│   ├── utils/                  # Domain-specific helpers
│   │   ├── docai.py            # Protobuf-to-JSON extraction logic
│   │   ├── formatters.py       # Markdown conversion for LLM context
│   │   ├── prompt_build.py     # Instruction assembly logic
│   │   └── prompt_templates.py # Specialized system prompts (Freeform, Structured, Arabic)
│   ├── exceptions/             # Standardized Error Handling
│   │   └── base.py             # APIException & ToolConfigurationException
│   ├── root_agent.py           # The Orchestrator Agent (Tool calling loop)
│   ├── prompts.py              # Orchestrator high-level instructions
│   ├── state.py                # ContextVars for multi-modal content handling
│   └── types.py                # Pipeline and Processor Enums
├── app/                        # Web Layer
│   └── main.py                 # FastAPI Application & Global Exception Handlers
├── main.py                     # Entry point (Uvicorn runner)
├── .env                        # Environment variables (secret)
└── requirements.txt            # Python dependencies
```

## Error Handling

The system uses a custom exception hierarchy to ensure consistent API responses:
- **`ToolConfigurationException`**: Raised during startup or execution if cloud services or credentials are misconfigured.
- **`APIException`**: A cross-layer exception that carries an HTTP status code, ensuring the API always returns structured JSON errors.

## Observability

Deep observability is built-in using **OpenTelemetry**:
- Automatic instrumentation of the FastAPI layer.
- Manual spans in the `root_agent` to track reasoning and tool execution times.
- Integration with Google Cloud Trace for production monitoring.

## Design Decisions

- **State Management**: Large document bytes are stored in `contextvars` rather than being passed through the LLM context, preventing token bloat and improving performance.
- **Async/Sync Bridge**: Backend services are fully asynchronous, while the Agent tool interface maintains a synchronous signature (using `asyncio.run` or `to_thread`) for maximum compatibility with the ADK `Runner`.
- **Markdown OCR**: OCR results are converted into optimized Markdown tables and lists before being sent to Gemini, which significantly improves the model's ability to reason over architectural layouts.
