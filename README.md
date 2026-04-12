# Job Scout

Autonomous job hunting tool for UK and worldwide remote positions.

## Features

- Multi-platform job discovery (Indeed UK, Reed, Totaljobs, RemoteOK, We Work Remotely, etc.)
- Intelligent job matching and filtering
- AI-powered CV tailoring
- Cover letter generation
- Application package preparation
- Tracking and analytics

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Search for jobs
job-scout search -q "software engineer" -l "UK Remote"

# List platforms
job-scout platforms list

# Show analytics
job-scout analytics

# Initialize configuration
job-scout init
```

## Configuration

Edit `config/config.yaml` to set your preferences:

- Personal details
- Job preferences (titles, keywords, salary)
- AI configuration (OpenAI/Anthropic)
- Platform settings

## Requirements

- Python 3.11+
- SQLite3
- AI API key (OpenAI or Anthropic)

## License

MIT