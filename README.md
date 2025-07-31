# 🚀 Multi-Agent RAG System

A comprehensive comparison platform for different AI agents (Llama 3.2 vs GPT-4o) built on the same knowledge base following Google ADK structure.

## ✨ Features

- **🤖 Multiple AI Agents**: Compare Llama 3.2 vs GPT-4o using the same knowledge base
- **🔄 Conversation Reformulation**: Enhanced memory handling and context maintenance
- **� Shared Knowledge Base**: Both agents use the same document corpus for fair comparison
- **🌐 ADK Compatible**: Follows Google ADK agent structure with `root_agent` pattern
- **�📊 3D Visualization**: Interactive t-SNE visualization in the Jupyter notebook
- **� Source Citations**: Transparent document sourcing in responses

## 🏗️ Project Structure

```
google-adk-hackathon/
├── knowledge-base-slack/          # 📚 Shared knowledge base
│   └── team_a/                    # Document folders
├── multi_tool_agent_llama/        # 🦙 Llama 3.2 Agent
│   ├── __init__.py
│   ├── agent.py                   # ADK entry point with root_agent
│   └── rag_kb_llm.py             # Llama RAG implementation
├── multi_tool_agent_openai/       # 🤖 OpenAI GPT-4o Agent  
│   ├── __init__.py
│   ├── agent.py                   # ADK entry point with root_agent
│   └── rag_kb_openai.py          # OpenAI RAG implementation
├── vector_embeddings_visualization.ipynb  # 📊 3D Visualization
├── compare_agents.py              # 🔍 Quick comparison tool
├── slack_listener.py              # 💬 Slack integration
└── pyproject.toml                # 📦 Dependencies
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.12+**
2. **Google ADK**: `pip install google-adk`
3. **Ollama** (for Llama): Install from [ollama.ai](https://ollama.ai)
4. **OpenAI API Key** (for GPT-4o)

### Installation

1. **Clone and setup:**
   ```bash
   cd google-adk-hackathon
   pip install -e .
   ```

2. **Environment setup:**
   ```bash
   # Create .env file with your OpenAI key
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

3. **Start Ollama:**
   ```bash
   ollama serve
   ollama pull llama3.2
   ```

## � Usage

### Using ADK Web (Recommended)

**Llama Agent:**
```bash
adk web multi_tool_agent_llama
```

**OpenAI Agent:**  
```bash
adk web multi_tool_agent_openai
```

### Quick Comparison

```bash
python compare_agents.py
```

### 3D Visualization

Open the Jupyter notebook:
```bash
jupyter notebook vector_embeddings_visualization.ipynb
```

## 🔧 Agent Comparison

| Feature | Llama 3.2 | GPT-4o |
|---------|-----------|--------|
| **Model** | Llama 3.2 (Ollama) | GPT-4o (OpenAI) |
| **Embeddings** | HuggingFace all-MiniLM-L6-v2 | HuggingFace all-MiniLM-L6-v2 |
| **Conversation Memory** | ✅ Enhanced with output_key | ✅ Enhanced with output_key |
| **Question Reformulation** | ✅ Verbose mode enabled | ✅ Verbose mode enabled |
| **Source Citations** | ✅ Top 3 sources shown | ✅ Top 3 sources shown |
| **Knowledge Base** | 📚 Shared knowledge-base-slack | 📚 Shared knowledge-base-slack |
| **Retrieval** | Top 5 relevant chunks | Top 5 relevant chunks |

## 💡 Sample Questions

Test both agents with these conversation flows:

1. **Basic Query:**
   ```
   "How do I book a parking space?"
   ```

2. **Follow-up (tests conversation reformulation):**
   ```
   Q1: "How do I book a parking space?"  
   Q2: "What about for someone else?"
   ```
   ✅ Should reformulate Q2 to: "How do I book a parking space for someone else?"

3. **Context Switch:**
   ```
   Q1: "How do I book a parking space?"
   Q2: "What's the process for organizing an event?"
   Q3: "How do I add speakers?"
   ```
   ✅ Q3 should be understood in event context, not parking

## 📊 Key Improvements

### Enhanced Conversation Handling
Both agents now feature:
- **Question Reformulation**: Ambiguous follow-ups reformulated using conversation context
- **Memory Management**: Proper `ConversationBufferMemory` with `output_key='answer'`
- **Verbose Output**: See question reformulation process in real-time
- **Source Citations**: Transparent document sourcing

### Example Conversation:
```
User: "How do I book a parking space?"
Agent: [Detailed parking booking steps with sources]

User: "What about for someone else?"
System: Reformulating → "How do I book a parking space for someone else?"
Agent: [Specific booking steps for others with sources]
```

## 🛠️ Development

### ADK Agent Structure

Each agent follows the ADK pattern:
```python
# agent.py
from google.adk.agents import Agent
from . import rag_kb_implementation

def chat_kb(question: str) -> dict:
    # Implementation

root_agent = Agent(
    name="agent_name",
    model="model_name", 
    description="Agent description",
    instruction="Agent instructions",
    tools=[chat_kb],
)
```

### Adding New Agents

1. Create new folder: `multi_tool_agent_newmodel/`
2. Implement: `rag_kb_newmodel.py` with `chat()` function
3. Create: `agent.py` with `root_agent` 
4. Use shared `knowledge-base-slack/` directory

## 🔍 Troubleshooting

**Ollama Issues:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Restart if needed
ollama serve
```

**OpenAI Issues:**
- Verify API key in `.env` file
- Check OpenAI account credits

**ADK Issues:**
```bash
# Verify ADK installation
adk --version

# Check agent structure
adk web multi_tool_agent_llama --debug
```

## 📈 Performance Comparison

Both agents now have equivalent conversation handling:
- ✅ Same conversation reformulation capabilities
- ✅ Same memory configuration
- ✅ Same source citation format  
- ✅ Same knowledge base access
- ✅ Same embedding model for fair comparison

The main differences are in the underlying LLM capabilities (Llama 3.2 vs GPT-4o) rather than the RAG implementation.

## 🤝 Contributing

1. Follow the ADK agent structure pattern
2. Use the shared `knowledge-base-slack/` for consistency
3. Implement conversation reformulation with verbose output
4. Include source citations in responses
5. Test with `compare_agents.py`

## 📄 License

MIT License - See LICENSE file for details

---

🎉 **Ready to compare AI agents!** 

- **Quick test**: `python compare_agents.py`
- **Llama agent**: `adk web multi_tool_agent_llama`  
- **OpenAI agent**: `adk web multi_tool_agent_openai`
- **Visualization**: Open `vector_embeddings_visualization.ipynb`
