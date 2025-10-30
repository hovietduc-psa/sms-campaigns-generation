# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered SMS campaign generation API built with FastAPI. The service generates complete SMS campaigns from natural language descriptions using OpenAI GPT models (GPT-4o for planning, GPT-4o-mini for content generation). It includes comprehensive validation, quality scoring, template search via Qdrant vector database, and fallback support via GROQ.

## Development Commands

### Environment Setup
```bash
make install-dev        # Install development dependencies
python -m src.main     # Run development server (starts on localhost:8000)
make run-dev           # Run with reload flag
```

### Testing and Quality
```bash
make test              # Run pytest tests
make test-coverage     # Run tests with coverage report
make lint              # Run flake8, pylint, mypy
make format            # Format code with black and isort
make format-check      # Check code formatting
```

### Docker Development
```bash
make docker-build      # Build Docker image
make docker-run        # Start with docker-compose (includes Qdrant)
make docker-stop       # Stop docker-compose services
make docker-shell      # Get shell in running container
```

### Database and Templates
```bash
make seed-db           # Seed template database (API must be running)
make health            # Check API health status
```

### Quick Development Workflow
```bash
make dev               # Install deps and run server
```

## Architecture Overview

The application follows a layered service architecture:

**Core Pipeline (src/services/campaign_generation/)**:
- `orchestrator.py` - Main coordination service that manages the entire generation pipeline
- `input_extractor.py` - Extracts campaign details from natural language input
- `planner.py` - Creates campaign structure and flow using GPT-4o
- `generator.py` - Generates message content using GPT-4o-mini
- `template_manager.py` - Handles template search and storage via Qdrant
- `behavioral_targeting.py` - Advanced behavioral targeting and personalization
- `advanced_template_engine.py` - Custom message structure and template mapping
- `scheduling_engine.py` - Campaign scheduling and timing optimization

**Validation (src/services/campaign_validation/)**:
- `validator.py` - Main validation coordinator
- `schema_validator.py` - JSON schema validation
- `flow_validator.py` - Campaign flow validation
- `best_practices_checker.py` - SMS marketing best practices
- `optimization_engine.py` - Campaign optimization suggestions

**API Layer (src/api/v1/)**:
- `campaigns.py` - FastAPI endpoints for campaign generation, validation, and template search

**Supporting Services**:
- `embeddings.py` - Text embedding service for semantic search
- `authentication.py` - API key authentication
- `metrics.py` - Observability and performance tracking

## Campaign Generation Process

1. **Input Extraction**: Parse natural language to extract campaign intent, parameters, and constraints
2. **Template Search**: Find similar campaigns using semantic search (Qdrant + Cohere embeddings)
3. **Structure Planning**: Plan campaign flow, steps, and logic (GPT-4o)
4. **Content Generation**: Generate message text and configurations (GPT-4o-mini)
5. **Validation**: Multi-layer validation (schema, flow, best practices)
6. **Quality Scoring**: A-F grading with optimization suggestions
7. **Output**: Complete campaign JSON ready for execution engine

## Key Dependencies

- **FastAPI** - Web framework with automatic OpenAPI documentation
- **OpenAI** - Primary AI models (GPT-4o, GPT-4o-mini)
- **GROQ** - Fallback AI provider
- **Qdrant** - Vector database for template search
- **Cohere** - Text embeddings for semantic search
- **Pydantic** - Data validation and settings management

## Environment Configuration

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key (primary AI provider)
- `GROQ_API_KEY` - GROQ API key (fallback provider)
- `API_KEY` - API authentication key

Optional variables:
- `QDRANT_URL`, `QDRANT_API_KEY` - Qdrant vector database configuration
- `COHERE_API_KEY` - Cohere embeddings API key
- `DEBUG` - Enable debug mode (default: false)
- `DATABASE_URL` - Database connection URL

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Health check endpoint: `http://localhost:8000/health`

## Testing Strategy

The project uses pytest for testing. Tests should cover:
- API endpoint functionality
- Campaign generation pipeline
- Validation logic
- Error handling and fallback scenarios
- Integration with external services (OpenAI, Qdrant)

## Production Deployment

The application is containerized with multi-stage Docker builds:
- Development stage includes all dev dependencies
- Production stage uses non-root user and minimal dependencies
- Docker Compose includes Qdrant for template search
- Health checks configured for both API and Qdrant services

## Cost and Performance

- Typical cost: ~$0.12 per campaign generation
- Expected latency: 4-6 seconds
- Automatic retry logic with fallback providers
- Real-time cost tracking and metadata