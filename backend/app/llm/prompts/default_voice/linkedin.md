I spent three weeks building something I thought would be straightforward — a multi-agent pipeline for automated test generation. It wasn't.

The architecture looked clean on paper: eight agents, each scoped to a single skill, handing off context through a shared state object. What I didn't account for was context bloat. By agent 4, the model was reading 12,000 tokens of prior conversation to answer a 200-token question. Token costs ballooned. Latency tripled.

The fix was brutal but obvious once I saw it: kill the shared context. Each agent gets only what it needs. A router summarises the handoff. Context per agent dropped 92%. Costs followed.

I've been building agentic AI systems for two years and the failure mode is always the same — we design for the happy path and don't stress-test context at scale. The model doesn't care how elegant your architecture diagram looks.

What's the ugliest production failure you've debugged in an LLM system?

#AIEngineering #LangGraph #AgentDesign
