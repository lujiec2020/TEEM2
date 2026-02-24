#DataScaffold: AI Multi-Agent System for Data Analysis 

An AI-powered multi-agent system designed to scaffold students through the data analysis pipeline. Rather than providing direct answers, DataScaffold guides learners step-by-step from raw data to visualization to insight to actionable recommendations, building genuine data literacy along the way.

---



## Development Roadmap

### Phase 1 : Data Collection + Agent 0 (Orchestrator)
- [ ] Design data ingestion pipeline (CSV, Excel, JSON)
- [ ] Build **Agent 0**: the orchestrator that converses with the student, understands their intent, and routes tasks to specialist agents
- [ ] Implement conversation memory and session management

### Phase 2 : Agent 1 (Visualization) + Model Selection
- [ ] Create **Agent 1**: generates appropriate visualizations based on the data and student's question
- [ ] Evaluate model options for code generation quality:
  - Top-tier proprietary models (Claude, GPT-4o)
  - Open-source alternatives (Code Llama, DeepSeek Coder) if cost/latency is a concern
- [ ] Benchmark: chart correctness, code runnability, visual clarity

### Phase 3 : Agent 2 (Insight Generation) + Model Selection
- [ ] Create **Agent 2**: analyzes visualizations and data to generate meaningful insights
- [ ] Find the best model for interpretive reasoning over charts and statistics
- [ ] Focus on distinguishing **descriptive ("Show")** vs. **interpretive ("Tell")** language

### Phase 4 : Agent 3 (Recommendation) + Model Selection
- [ ] Create **Agent 3**: provides actionable recommendations based on insights and visualizations
- [ ] Evaluate models for reasoning quality: can the model connect data patterns to concrete next steps?
- [ ] Implement scaffolding prompts that guide students toward their own conclusions before revealing suggestions

### Phase 5 : System Testing & Evaluation
- [ ] End-to-end integration testing across all agents
- [ ] Student user study: does the scaffolding improve learning outcomes?
- [ ] Measure: task completion, quality of student-written narratives, pre/post assessment gains
- [ ] Iterate on agent prompts and model selection based on results

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | LangChain + LangGraph |
| LLM Provider | not decide yet |
| Backend | FastAPI (Python) |
| Frontend | React |
| Deployment | AWS (EC2,Bedrock,S3,etc)


## License

UMBC

---