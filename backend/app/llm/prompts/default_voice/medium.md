The Hidden Cost of Multi-Agent Orchestration

Three months ago I ran a benchmark I didn't expect to run. I built the same task three ways: a bloated 7-agent pipeline, a lean single-agent with a skill library, and a hybrid in between. I expected the multi-agent version to win on quality. It didn't.

The bloated pipeline used 11.2× more tokens than the lean version for equivalent output. Latency was 23× worse. The quality delta was within noise. This wasn't a toy benchmark — it was a real JUnit test generation task, measured across 50 inputs.

The root cause is context. Multi-agent systems accumulate conversational overhead at every handoff. Each agent reads the prior agent's full output, the original task, and its own instructions. By agent five, you're paying for 15,000 tokens of setup to generate 500 tokens of work.

The fix isn't fewer agents. It's context scoping. Each agent should see only what it needs to complete its step. A router layer summarises state transitions instead of forwarding raw outputs. When I applied this, costs dropped 90% with no measurable quality loss.

The lesson I keep relearning: the model doesn't care about your architecture diagram. It cares about what's in context right now.
