# Tacto System

Restaurant automation and messaging system built with FastAPI, PostgreSQL, and AI integration.

## Architecture

This project follows Clean Architecture principles with the following layers:

- **Domain**: Core business logic and entities
- **Application**: Use cases and application logic
- **Infrastructure**: External integrations and data persistence
- **Interfaces**: HTTP APIs and background workers

## Features

- Restaurant management and automation
- AI-powered messaging and conversation handling
- Order processing and management
- Integration with Join messaging platform
- Vector-based memory and search capabilities

## Quick Start

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd tacto-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start services with Docker**
   ```bash
   docker-compose up -d
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

## Development

### Code Style
```bash
black .
isort .
mypy .
```

### Testing
```bash
pytest
```

## Documentation

See the `/docs` directory for detailed documentation:
- Architecture overview
- API specifications
- Database schema
- AI flows and integration details

## License

MIT License - see LICENSE file for details.
