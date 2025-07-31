# 🤖 ADK Agents Directory

This directory contains all ADK (Agent Development Kit) agents for the RAG system. Run `adk web` from this directory to see only the agents in the dropdown.

## 🚀 Quick Start

```bash
# Navigate to agents directory
cd agents

# Run ADK web interface (shows only agents)
adk web

# Access at: http://localhost:8000
```

## 📁 Agent Structure

### `llama_agent/` - Local Llama 3.2 Agent
- **Model**: Llama 3.2 (via Ollama)
- **Cost**: Free (local inference)
- **Speed**: ~5.5 seconds per response
- **Memory**: Enhanced conversation handling
- **Vector DB**: `../vector_db_llama/`

### `openai_agent/` - OpenAI GPT-4o Agent  
- **Model**: GPT-4o (cloud API)
- **Cost**: ~$0.01-0.03 per query
- **Speed**: ~4.9 seconds per response
- **Memory**: Enhanced conversation handling
- **Vector DB**: `../vector_db_openai/`

## 🎯 Features

### Both Agents Include:
- ✅ **Smart Vector Caching** - No embedding recreation
- ✅ **Shared Knowledge Base** - `../knowledge-base-slack/`
- ✅ **Source Citations** - Document references in responses
- ✅ **Conversation Memory** - Context-aware follow-up questions
- ✅ **Optimized Performance** - 70% faster startup times

### Knowledge Base Categories:
- **Events**: Event planning and management
- **Parking**: Parking reservations and management  
- **Locations**: Office locations and directions
- **Platform**: Technical platform information
- **Service Requests**: Support ticket procedures

## 🧪 Testing

```bash
# Test individual agents
python -c "from llama_agent.agent import root_agent; print('Llama:', root_agent.name)"
python -c "from openai_agent.agent import root_agent; print('OpenAI:', root_agent.name)"

# Run comparison tests (from project root)
cd .. && python compare_agents.py

# Performance testing (from project root)  
cd .. && python performance_test.py
```

## 📊 Performance Comparison

| Metric | Llama Agent | OpenAI Agent |
|--------|-------------|--------------|
| **Model** | Llama 3.2 (local) | GPT-4o (cloud) |
| **Startup** | ~11 seconds | ~8 seconds |
| **Response** | ~5.5 seconds | ~4.9 seconds |
| **Cost** | Free | ~$0.01/query |
| **Quality** | High | Very High |

## 🔧 Configuration

Both agents use:
- **Environment**: `.env` file in this directory
- **Dependencies**: `pyproject.toml` for package management
- **Vector Storage**: Project root level databases
- **Knowledge Base**: Shared `../knowledge-base-slack/` directory

## 📝 Sample Questions

```
"How do I book a parking space?"
"What's the process for organizing an event?"
"How do I submit a service request?"
"Where can I find location information?"
"How do I access the platform?"
```

## 🏗️ Architecture

```
agents/
├── .env                 # Environment variables
├── pyproject.toml       # Dependencies
├── llama_agent/         # Local Llama 3.2 agent
│   ├── agent.py         # ADK agent entry point
│   ├── rag_kb_llm.py    # RAG implementation
│   └── __init__.py      # Package init
└── openai_agent/        # OpenAI GPT-4o agent
    ├── agent.py         # ADK agent entry point
    ├── rag_kb_openai.py # RAG implementation
    └── __init__.py      # Package init
```

## 🎉 Usage Notes

- **Development**: Use Llama agent (free local testing)
- **Production**: Use OpenAI agent (faster, more reliable)
- **Comparison**: Both agents provide high-quality responses
- **Scaling**: Vector databases cached for fast subsequent runs

---
*ADK agents ready for production use! 🚀*
