import os

file_descriptions = {
    ".github/workflows/backend-ci.yml": "CI workflow for testing and linting the backend.",
    ".github/workflows/frontend-ci.yml": "CI workflow for building and testing the frontend.",
    "Makefile": "Build and deployment commands for the project.",
    "PHOENIX_OBSERVABILITY.md": "Documentation for Phoenix observability setup.",
    "README.md": "Main project documentation and overview.",
    "aws_deploy.py": "Script to deploy the application to AWS.",
    "backend/Dockerfile": "Docker configuration for building the backend image.",
    "backend/app/agents/__init__.py": "Initialization for the AI agents module.",
    "backend/app/agents/analysis_agent.py": "Agent responsible for analyzing research data.",
    "backend/app/agents/evaluation_agent.py": "Agent for evaluating research findings.",
    "backend/app/agents/planner_agent.py": "Agent for planning the research steps.",
    "backend/app/agents/report_agent.py": "Agent for compiling and generating research reports.",
    "backend/app/agents/research_graph.py": "LangGraph definitions for the research workflow.",
    "backend/app/agents/retrieval_agent.py": "Agent for retrieving context from vector stores.",
    "backend/app/agents/search_agent.py": "Agent for performing web searches.",
    "backend/app/api/__init__.py": "Initialization for the API module.",
    "backend/app/api/v1/__init__.py": "Initialization for the v1 API routes.",
    "backend/app/api/v1/router.py": "Main API router for version 1 endpoints.",
    "backend/app/core/__init__.py": "Initialization for the core application logic.",
    "backend/app/core/cache.py": "Caching mechanisms and Redis configuration.",
    "backend/app/core/config.py": "Application configuration and environment variables.",
    "backend/app/core/dependencies.py": "FastAPI dependencies for injection.",
    "backend/app/core/llm.py": "Core Large Language Model initialization.",
    "backend/app/core/logging_config.py": "Configuration for application logging.",
    "backend/app/core/memory.py": "Memory management for conversation history.",
    "backend/app/core/security.py": "Security and authentication utilities.",
    "backend/app/core/task_manager.py": "Management of asynchronous tasks.",
    "backend/app/evaluation/answer_scorer.py": "Logic for scoring generated answers.",
    "backend/app/evaluation/hallucination_checker.py": "Checks for hallucinations in generated content.",
    "backend/app/evaluation/relevance_evaluator.py": "Evaluates relevance of retrieved documents.",
    "backend/app/evaluation/research_quality.py": "Assesses the overall quality of research.",
    "backend/app/evaluation/source_validator.py": "Validates the credibility of sources.",
    "backend/app/knowledge_graph/__init__.py": "Initialization for the knowledge graph module.",
    "backend/app/knowledge_graph/entity_extractor.py": "Extracts entities for the knowledge graph.",
    "backend/app/knowledge_graph/graph_builder.py": "Builds and manages the knowledge graph.",
    "backend/app/knowledge_graph/graph_query_engine.py": "Engine for querying the knowledge graph.",
    "backend/app/knowledge_graph/graph_store.py": "Storage interface for the knowledge graph.",
    "backend/app/knowledge_graph/relation_extractor.py": "Extracts relationships between entities.",
    "backend/app/knowledge_graph/research_memory_graph.py": "Manages graph representation of research memory.",
    "backend/app/llm/__init__.py": "Initialization for the LLM abstractions.",
    "backend/app/llm/fallback_manager.py": "Manages fallback logic for LLM providers.",
    "backend/app/llm/model_registry.py": "Registry of available LLM models.",
    "backend/app/llm/providers/__init__.py": "Initialization for LLM providers.",
    "backend/app/llm/providers/base_provider.py": "Base interface for LLM providers.",
    "backend/app/llm/providers/groq_provider.py": "Groq integration for LLM.",
    "backend/app/llm/providers/ollama_provider.py": "Ollama integration for local LLM.",
    "backend/app/llm/providers/openai_provider.py": "OpenAI integration for LLM.",
    "backend/app/llm/router.py": "Routes LLM requests to appropriate providers.",
    "backend/app/llm/token_monitor.py": "Monitors LLM token usage and limits.",
    "backend/app/main.py": "Main FastAPI application entry point.",
    "backend/app/mcp/__init__.py": "Initialization for the Model Context Protocol module.",
    "backend/app/mcp/base_tool.py": "Base class for MCP tools.",
    "backend/app/mcp/tool_executor.py": "Executes MCP tools.",
    "backend/app/mcp/tool_registry.py": "Registry for available MCP tools.",
    "backend/app/mcp/tools/extraction_tool.py": "MCP tool for data extraction.",
    "backend/app/mcp/tools/report_tool.py": "MCP tool for report generation.",
    "backend/app/mcp/tools/rerank_tool.py": "MCP tool for document reranking.",
    "backend/app/mcp/tools/retrieval_tool.py": "MCP tool for document retrieval.",
    "backend/app/mcp/tools/search_tool.py": "MCP tool for searching information.",
    "backend/app/middleware/rate_limit.py": "Middleware for API rate limiting.",
    "backend/app/middleware/request_logging.py": "Middleware for logging API requests.",
    "backend/app/models/api_models.py": "Pydantic models for API requests and responses.",
    "backend/app/models/job_models.py": "Pydantic models for background jobs.",
    "backend/app/models/state.py": "State management models for the application.",
    "backend/app/observability/__init__.py": "Initialization for observability and tracing.",
    "backend/app/observability/llm_instrumentation.py": "Instrumentation for LLM tracing.",
    "backend/app/observability/phoenix_tracer.py": "Arize Phoenix integration for tracing.",
    "backend/app/observability/rag_instrumentation.py": "Instrumentation for RAG tracing.",
    "backend/app/rag/__init__.py": "Initialization for Retrieval-Augmented Generation.",
    "backend/app/rag/chunker.py": "Logic for chunking documents for indexing.",
    "backend/app/rag/embedding.py": "Embedding generation for documents.",
    "backend/app/rag/reranker.py": "Reranks retrieved documents for better relevance.",
    "backend/app/rag/vector_store.py": "Vector database interface (e.g., Qdrant).",
    "backend/app/realtime/event_models.py": "Models for real-time WebSocket events.",
    "backend/app/realtime/stream_service.py": "Service for managing data streams.",
    "backend/app/realtime/sync_publisher.py": "Publishes real-time events synchronously.",
    "backend/app/realtime/websocket_manager.py": "Manages WebSocket connections and broadcasting.",
    "backend/app/routes/__init__.py": "Initialization for application routes.",
    "backend/app/routes/agentic_research.py": "API endpoints for agentic research workflows.",
    "backend/app/routes/async_research.py": "API endpoints for asynchronous research.",
    "backend/app/routes/deep_research.py": "API endpoints for deep research features.",
    "backend/app/routes/mcp_tools.py": "API endpoints for MCP tools integration.",
    "backend/app/routes/research.py": "Standard API endpoints for research.",
    "backend/app/routes/search.py": "API endpoints for search functionality.",
    "backend/app/services/__init__.py": "Initialization for business logic services.",
    "backend/app/services/answer_service.py": "Service for generating final answers.",
    "backend/app/services/context_builder.py": "Builds context from retrieved documents for LLMs.",
    "backend/app/services/extraction_service.py": "Service for extracting structured data.",
    "backend/app/services/history_service.py": "Manages conversation and research history.",
    "backend/app/services/indexing_service.py": "Service for indexing documents into the vector store.",
    "backend/app/services/job_service.py": "Manages background jobs and their status.",
    "backend/app/services/search_service.py": "Core logic for performing searches.",
    "backend/app/services/session_service.py": "Manages user sessions.",
    "backend/app/utils/__init__.py": "Initialization for utility functions.",
    "backend/app/utils/json_parser.py": "Utility for robust JSON parsing.",
    "backend/app/workers/__init__.py": "Initialization for background workers.",
    "backend/app/workers/celery_app.py": "Celery application configuration for background tasks.",
    "backend/app/workers/research_tasks.py": "Celery tasks for asynchronous research execution.",
    "backend/pytest.ini": "Configuration for pytest.",
    "backend/tests/conftest.py": "Fixtures and configuration for backend tests.",
    "backend/tests/test_api.py": "Tests for the API endpoints.",
    "backend/tests/test_core.py": "Tests for core application functionality.",
    "backend/tests/test_eval.py": "Tests for evaluation mechanisms.",
    "backend/tests/test_rag.py": "Tests for RAG components.",
    "docker-compose.yml": "Docker Compose configuration for running the application stack.",
    "frontend/Dockerfile": "Docker configuration for building the frontend image.",
    "frontend/README.md": "Frontend specific documentation.",
    "frontend/eslint.config.js": "ESLint configuration for frontend code.",
    "frontend/index.html": "Main HTML entry point for the frontend.",
    "frontend/src/App.css": "Main styling for the React application.",
    "frontend/src/App.jsx": "Root React component for the frontend.",
    "frontend/src/api/client.js": "API client for communicating with the backend.",
    "frontend/src/components/MetricsDashboard.jsx": "Component displaying research metrics.",
    "frontend/src/components/ProgressTracker.jsx": "Component tracking background job progress.",
    "frontend/src/components/ReportViewer.jsx": "Component for viewing generated reports.",
    "frontend/src/components/ResearchForm.jsx": "Form component for starting new research.",
    "frontend/src/components/SourceViewer.jsx": "Component for viewing research sources.",
    "frontend/src/components/research/LiveResearchFeed.jsx": "Component displaying live updates from research tasks.",
    "frontend/src/components/research/WorkflowTimeline.jsx": "Component showing the timeline of the research workflow.",
    "frontend/src/hooks/useResearch.js": "Custom hook for managing research state.",
    "frontend/src/hooks/useResearchStream.js": "Custom hook for managing WebSocket research streams.",
    "frontend/src/index.css": "Global CSS styles.",
    "frontend/src/main.jsx": "Frontend application entry point and React root rendering.",
    "frontend/src/pages/Dashboard.jsx": "Main dashboard page component.",
    "frontend/tests/Dashboard.test.js": "Tests for the Dashboard component.",
    "frontend/vite.config.js": "Vite bundler configuration for the frontend."
}

def get_comment_string(filepath, desc):
    basename = os.path.basename(filepath)
    if filepath.endswith('.py') or filepath.endswith('.yml') or filepath.endswith('.yaml') or filepath.endswith('.ini') or basename == 'Makefile' or basename == 'Dockerfile':
        return f"# {basename} - {desc}\n"
    elif filepath.endswith('.js') or filepath.endswith('.jsx') or filepath.endswith('.css'):
        return f"// {basename} - {desc}\n"
    elif filepath.endswith('.html') or filepath.endswith('.md'):
        return f"<!-- {basename} - {desc} -->\n"
    else:
        return f"# {basename} - {desc}\n"

for filepath, desc in file_descriptions.items():
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        comment = get_comment_string(filepath, desc)
        
        # Don't add twice
        if content.startswith(comment.strip()):
            continue
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(comment + content)
            
print("Added comments to all files.")
