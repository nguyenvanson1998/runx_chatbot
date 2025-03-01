# RunX Health Chatbot 🚀🏃‍♂️

## Introduction

RunX is an innovative health and fitness platform that rewards your commitment to wellness. Our unique approach combines advanced health tracking, personalized coaching, and blockchain technology to create a comprehensive ecosystem where **"You Get Fit, You Get Paid!"** 💪💰

### Key Features:

- **Fitness Rewards**: Earn rewards for your health activities and achievements
- **Advanced Health Tracking**: Monitor vital health metrics through the RunX Ring
- **Zero Gas Fees**: Seamless blockchain integration through RunX's PayNetwork
- **Supportive Community**: Connect with like-minded fitness enthusiasts

This repository contains a health-focused chatbot built to help users understand their health metrics, get personalized advice, and learn more about the RunX ecosystem.

## Using the RunX Health Chatbot

The RunX chatbot allows you to interact naturally through conversation to get information about:

### Health Metrics & Monitoring

Ask questions about metrics tracked by the RunX Ring:
- "What can the RunX Ring measure?"
- "How does blood glucose monitoring work?"
- "Tell me about sleep analysis features"

### Fitness Guidance

Get personalized advice:
- "How can I improve my sleep quality?"
- "What's a good resting heart rate?"
- "How can I track my fitness progress?"

### RunX Platform Information

Learn more about the platform:
- "How does RunX reward system work?"
- "Tell me more about the blockchain integration"
- "What makes the RunX Ring unique?"

## Local Installation

Follow these steps to set up the RunX chatbot locally:

### Prerequisites

- Python 3.11 or higher
- pip (Python package installer)

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/runX-chatbot.git
cd runX-chatbot
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory with the following contents:

```
OPENAI_API_KEY=your_openai_api_key
CHAINLIT_AUTH_SECRET=your_secret_key
DATABASE_URL=sqlite+aiosqlite:///data/runx.db
AUTH_API_URL=https://api.runx.app/api/v1/auth/signin
```

5. **Run the application**

```bash
chainlit run app.py
```

The chatbot will be available at `http://localhost:8000` in your browser.

## Docker Installation

For a containerized setup, use Docker:

### Prerequisites

- Docker
- Docker Compose (optional, for easier management)

### Using Docker Compose

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/runX-chatbot.git
cd runX-chatbot
```

2. **Create a docker-compose.yml file**

```yaml
version: '3.8'

services:
  runx-chatbot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: runx-chatbot
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      # Only mount the data directory for database persistence
      - ./data:/app/data
    env_file:
      - .env
```
3. **Build and run the container**

```bash
docker-compose up -d
```

### Using Docker Directly

1. **Build the Docker image**

```bash
docker build -t runx-chatbot .
```

2. **Run the container**

```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_openai_api_key \
  -e CHAINLIT_AUTH_SECRET=your_secret_key \
  -e DATABASE_URL=sqlite+aiosqlite:///data/runx.db \
  -e AUTH_API_URL=https://api.runx.app/api/v1/auth/signin \
  -v $(pwd)/data:/app/data \
  runx-chatbot
```

The chatbot will be available at `http://localhost:8000` in your browser.

## Learn More

For more information about RunX, visit:
- Official website: [https://runx.app/](https://runx.app/)
- Documentation: [https://docs.runx.app/](https://docs.runx.app/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
