FROM python:3.11-slim

# ping is not included in slim images by default
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY agent.py .

ENV MONITOR_HOSTS="8.8.8.8,1.1.1.1"
ENV CHECK_INTERVAL_SECONDS=15
ENV AGENT_PORT=9105
ENV DOWN_THRESHOLD=3

EXPOSE 9105

CMD ["python", "agent.py"]
