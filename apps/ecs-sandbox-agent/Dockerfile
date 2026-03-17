# Build context is the repository root
FROM python:3.12-slim

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY apps/ecs-sandbox-agent/agent.py /agent.py
COPY apps/ecs-sandbox-agent/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

EXPOSE 2222
CMD ["python", "/agent.py"]
