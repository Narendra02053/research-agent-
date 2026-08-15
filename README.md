<!-- README.md - Main project documentation and overview. -->
# AI Deep Research Agent

A full-stack, production-ready AI research platform that leverages LangGraph, FastAPI, Celery, and React to autonomously plan, search, retrieve, synthesize, and evaluate comprehensive research reports.

## Architecture

*   **Frontend**: React, Vite, Tailwind CSS v4, Axios
*   **Backend API**: FastAPI, Pydantic, Python 3.11
*   **Agent Orchestration**: LangGraph
*   **Asynchronous Workers**: Celery
*   **Message Broker & Cache**: Redis
*   **Vector Database**: Qdrant

## Deployment Instructions (Docker)

The easiest way to run the entire stack locally or on a cloud virtual machine is using Docker Compose.

### Prerequisites

*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine installed.
*   Docker Compose installed.

### Setup Environment

1.  Navigate to the `backend/` directory.
2.  Copy `.env.example` to `.env`:
    ```bash
    cp backend/.env.example backend/.env
    ```
3.  Add your API keys to `backend/.env`:
    *   `TAVILY_API_KEY`: Get one from [Tavily](https://tavily.com/).
    *   `GROQ_API_KEY`: Get one from [Groq](https://console.groq.com/keys).

*(Note: In the Docker Compose environment, `REDIS_HOST` and `QDRANT_HOST` are automatically mapped to their respective containers. Do not change them to `localhost` in the `.env` file if running via Docker).*

### Running the Stack

Run the following command from the root of the repository:

```bash
docker-compose up --build -d
```

This will build and start 5 containers:
1.  **research_qdrant**: Vector database (port 6333)
2.  **research_redis**: Message broker and caching (port 6379)
3.  **research_backend**: FastAPI application (port 8000)
4.  **research_worker**: Celery asynchronous worker executing LangGraph tasks
5.  **research_frontend**: React frontend served via Nginx (port 3000)

### Accessing the Platform

*   **Frontend UI**: [http://localhost:3000](http://localhost:3000)
*   **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Troubleshooting

*   **Frontend cannot connect to backend**: Ensure the API proxy is correctly configured. In production, Nginx proxies `/api` to the backend container automatically.
*   **Jobs stay "pending"**: Check if the Celery worker is running by inspecting its logs: `docker logs research_worker`. Ensure Redis is healthy.
*   **Missing API Keys**: If search fails or the LLM generates an error, double-check your `backend/.env` file and restart the backend containers: `docker-compose restart backend worker`.

## Cloud Deployment Readiness

This stack is architected for cloud-native deployment. 
*   **AWS/GCP/Azure**: Deploy the `docker-compose.yml` via ECS or a standard VM.
*   **Kubernetes**: The stateless backend and worker architecture allows horizontal scaling. Simply create Deployments for `backend` and `worker`, and point them to managed Redis (e.g., AWS ElastiCache) and Qdrant clusters.
