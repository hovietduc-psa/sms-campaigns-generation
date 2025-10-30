# Campaign Generation API

A standalone API service for AI-powered SMS campaign generation, extracted from the main SMS agent application.

## Features

- **Natural Language to Campaign**: Generate complete SMS campaigns from natural language descriptions
- **AI-Powered Planning**: Uses GPT-4o for campaign structure planning
- **Content Generation**: Uses GPT-4o-mini for cost-effective content generation
- **Template Library**: Semantic search for similar campaign templates (requires Qdrant)
- **Comprehensive Validation**: Multi-layer validation including schema, flow, and best practices
- **Quality Scoring**: A-F grading based on SMS best practices
- **Fallback Support**: GROQ support as backup to OpenAI

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the server**:
```bash
python -m src.main
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Generate Campaign
```http
POST /api/v1/campaigns/generate
```

Generate a complete SMS campaign from a natural language description.

**Request**:
```json
{
    "merchant_id": "merchant_123",
    "description": "Create a flash sale campaign offering 20% off everything. Send initial message, then follow up after 6 hours if no click.",
    "campaign_type": "promotional",
    "use_template": true
}
```

**Response**:
```json
{
    "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
    "campaign_json": {
        "initialStepID": "step_001",
        "steps": [...]
    },
    "generation_metadata": {
        "total_cost_usd": 0.12,
        "duration_seconds": 4.5,
        "model_planning": "gpt-4o",
        "model_content": "gpt-4o-mini"
    },
    "validation": {
        "is_valid": true,
        "issues": [],
        "warnings": []
    },
    "status": "ready"
}
```

### Validate Campaign
```http
POST /api/v1/campaigns/validate
```

Validate a campaign JSON structure comprehensively.

### Search Templates
```http
POST /api/v1/campaigns/templates/search
```

Search for similar campaign templates using semantic search.

### Get Campaign Types
```http
GET /api/v1/campaigns/types
```

Get list of supported campaign types.

## Configuration

### Required Environment Variables

- `OPENAI_API_KEY`: OpenAI API key (primary)
- `GROQ_API_KEY`: GROQ API key (fallback)
- `API_KEY`: Your API authentication key

### Optional Environment Variables

- `QDRANT_URL`: Qdrant server URL for template search
- `QDRANT_API_KEY`: Qdrant API key
- `COHERE_API_KEY`: Cohere API key for embeddings
- `DATABASE_URL`: Database connection URL
- `DEBUG`: Enable debug mode

## Architecture

```
src/
├── api/v1/
│   └── campaigns.py          # API endpoints
├── core/
│   ├── config.py            # Configuration settings
│   └── database.py          # Database connection
├── models/
│   ├── campaign.py          # Campaign data models
│   └── campaign_generation.py # API request/response models
├── services/
│   ├── campaign_generation/ # Core generation services
│   │   ├── orchestrator.py  # Main coordination service
│   │   ├── planner.py       # Campaign structure planning
│   │   ├── generator.py     # Content generation
│   │   └── template_manager.py # Template search & storage
│   ├── campaign_validation/ # Validation services
│   ├── campaign_prompts/    # AI prompts
│   └── embeddings.py        # Text embedding service
├── security/
│   └── authentication.py   # API authentication
├── observability/
│   └── metrics.py          # Metrics collection
└── main.py                 # FastAPI application
```

## Campaign Generation Process

1. **Intent Extraction**: Extract campaign type and goals from natural language
2. **Template Search**: Find similar templates (if enabled)
3. **Structure Planning**: Plan campaign flow and steps
4. **Content Generation**: Generate message text and step configurations
5. **Validation**: Comprehensive validation and quality scoring
6. **Output**: Complete campaign JSON ready for execution

## Cost & Performance

- **Cost**: ~$0.12 per campaign (GPT-4o + GPT-4o-mini)
- **Latency**: 4-6 seconds typical
- **Quality**: A-F grading with optimization suggestions
- **Retry Logic**: Automatic retry with fallback strategies

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/
isort src/
```

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
CMD ["python", "-m", "src.main"]
```

### Environment Variables for Production
- Set `DEBUG=false`
- Use strong `API_KEY` values
- Configure proper database URL
- Set up monitoring and logging

## License

This code is extracted from the main SMS agent application and maintains the same licensing terms.