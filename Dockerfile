FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including sqlite
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Create data directory for database
RUN mkdir -p /app/data

# Create entrypoint script that properly handles db setup
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Run database setup script once\n\
echo "Running database setup..."\n\
cd /app && python -m db.db_setup\n\
\n\
# Start the Chainlit application\n\
echo "Starting RunX Chatbot..."\n\
exec chainlit run /app/app.py --port 8000 --host 0.0.0.0\n\
' > /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]