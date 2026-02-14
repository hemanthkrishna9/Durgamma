FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and agent templates
COPY backend/ ./
COPY agent-templates/ /agent-templates/

# Create missions directory
RUN mkdir -p /missions

ENV MC_AGENT_TEMPLATES_DIR=/agent-templates
ENV MC_MISSIONS_DIR=/missions
ENV MC_DATABASE_URL=sqlite+aiosqlite:////data/mission_control.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
