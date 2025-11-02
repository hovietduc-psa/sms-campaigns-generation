# SMS Campaign Generation System

Automated SMS Campaign Flow Generation using LLM technology.

## Overview

This system leverages Large Language Models (LLM) to automatically generate high-quality SMS campaign flows from simple natural language descriptions. It transforms marketing concepts into structured JSON flows that conform to the FlowBuilder schema, making campaign creation faster and more efficient.

## Features

- **Natural Language Input**: Convert campaign descriptions into executable flows
- **Complete FlowBuilder Support**: All 16+ node types supported
- **Schema Validation**: Comprehensive validation ensures generated flows are immediately usable
- **Auto-correction**: Intelligent error correction for common issues
- **REST API**: Clean API for integration with existing systems
- **High Performance**: Async architecture with caching and optimization
- **Monitoring**: Built-in metrics and health checks

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- PostgreSQL and Redis (optional, can use Docker)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sms-campaign-generation
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Install dependencies for local development**
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev,security]
   ```

### Usage

1. **Start the development server**
   ```bash
   python -m src.api.main
   # or
   uvicorn src.api.main:app --reload
   ```

2. **Generate a campaign flow**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/generateFlow" \
     -H "Content-Type: application/json" \
     -d '{"campaignDescription": "boost VIP reorders"}'
   ```

3. **View API documentation**
   Visit `http://localhost:8000/docs` for interactive API documentation.

## API Documentation

### Generate Campaign Flow

**POST** `/api/v1/generateFlow`

Generate an SMS campaign flow from a natural language description.

**Request:**
```json
{
  "campaignDescription": "nurture first-time buyers with abandoned cart recovery and personalized offers"
}
```

**Response:**
```json
{
  "initialStepID": "welcome-message",
  "steps": [
    {
      "id": "welcome-message",
      "type": "message",
      "content": "Hi {{first_name}}, thanks for your first purchase!",
      "events": [...]
    }
  ],
  "metadata": {
    "generated_at": "2024-01-01T00:00:00Z",
    "model_used": "gpt-4-turbo-preview",
    "tokens_used": 1500,
    "generation_time_ms": 3500
  }
}
```

## Supported Node Types

The system supports all FlowBuilder node types:

- **MESSAGE**: SMS messages with discounts, images, contact cards
- **SEGMENT**: Audience branching with conditions
- **DELAY**: Time delays
- **SCHEDULE**: Time-based branching
- **EXPERIMENT**: A/B testing
- **RATE_LIMIT**: Message frequency control
- **REPLY**: Handle specific reply intents
- **NO_REPLY**: Handle no-response scenarios
- **SPLIT**: Generic branching
- **PROPERTY**: Set customer properties
- **PRODUCT_CHOICE**: Interactive product selection
- **PURCHASE_OFFER**: Cart recovery with discounts
- **PURCHASE**: Complete purchases
- **LIMIT**: Occurrence limits
- **END**: Flow termination

## Development

### Project Structure

```
src/
├── api/                    # API layer
│   ├── endpoints/         # API endpoints
│   ├── middleware/        # Middleware components
│   └── main.py           # FastAPI application
├── core/                  # Core components
│   ├── config.py         # Configuration
│   ├── database.py       # Database management
│   └── logging.py        # Logging setup
├── models/               # Data models
├── services/             # Business logic
│   ├── llm_engine/       # LLM integration
│   ├── validation/       # Flow validation
│   └── cache/           # Caching layer
└── utils/               # Utilities
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test categories
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/
```

### Environment Variables

See `.env.example` for all available configuration options:

- `OPENAI_API_KEY`: OpenAI API key (required)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key
- `DEBUG`: Enable debug mode
- `LOG_LEVEL`: Logging level

## Architecture

The system consists of several key components:

1. **API Layer**: FastAPI application with endpoints and middleware
2. **LLM Engine**: OpenAI integration with sophisticated prompt engineering
3. **Validation Layer**: Multi-layer validation for schema and flow logic
4. **Database Layer**: PostgreSQL for logging and analytics
5. **Caching Layer**: Redis for performance optimization

## Performance

- **Response Time**: <10 seconds for simple campaigns, <30 seconds for complex
- **Success Rate**: >95% of requests produce valid flows
- **Concurrency**: Async architecture handles multiple simultaneous requests
- **Caching**: Intelligent caching reduces redundant LLM calls

## Monitoring

- **Health Checks**: `/health` endpoint for service health
- **Metrics**: Built-in performance and usage metrics
- **Logging**: Structured JSON logging with correlation IDs
- **Error Tracking**: Comprehensive error handling and reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please create an issue in the repository or contact the development team.