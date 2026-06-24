---
name: add-platform-generator
description: Bootstrap a new platform generator (LinkedIn, X, Medium, or future). Creates the generator class, cascade configuration, system prompt, adherence rules, and test scaffold. Use when adding support for a new social platform.
---

# Add Platform Generator

Use this skill when adding a new platform to the agent (e.g., Threads, Bluesky, Hashnode, dev.to). It creates all six files needed for a complete new platform integration and wires it into the LangGraph fan-out.

## What this skill creates

For a new platform `<name>` (lowercase, single word):

1. `backend/app/graph/nodes/generators/<name>.py` — generator class
2. `backend/app/llm/prompts/<name>_gen.md` — system prompt
3. `backend/app/evals/adherence/<name>_rules.py` — platform rules
4. `backend/tests/generators/test_<name>.py` — test scaffold
5. Updates `backend/app/llm/cascade.py` — adds cascade entry
6. Updates `backend/app/graph/builder.py` — wires into fan-out

## Required inputs

Before running, gather these from the user:

1. **Platform name** (e.g., `threads`, `bluesky`)
2. **Character limit** (single post, or `null` if effectively unlimited)
3. **Long-form?** Yes/no (affects model cascade choice)
4. **Format style** (one of: short_burst / professional_long / article)
5. **Key constraints** (hashtag rules, link rules, format rules)
6. **Three example posts** from this platform that match Ashwin's target voice (used in the system prompt as anchors)

## Steps

### 1. Generator class

Create `backend/app/graph/nodes/generators/<name>.py`:

```python
from app.graph.nodes.generators.base import PlatformGenerator
from app.graph.state import AgentState

class <Name>Generator(PlatformGenerator):
    platform = "<name>"
    system_prompt_path = "<name>_gen.md"
    cascade_key = "<name>_gen"

    def build_user_message(self, state: AgentState) -> str:
        examples = state["style_examples"].get("<name>", [])
        research = state.get("research_results")
        return render_template(
            "user_message.j2",
            context=state["context"],
            examples=examples,
            research=research,
        )
```

### 2. System prompt

Create `backend/app/llm/prompts/<name>_gen.md` with:
- Platform identity and audience description
- Format constraints (length, hashtags, structure)
- Voice guidance ("match the user's past posts in tone")
- The three example posts as anchors
- Output format spec (raw text only, no preamble)

### 3. Adherence rules

Create `backend/app/evals/adherence/<name>_rules.py`:

```python
from app.evals.adherence.base import Rule

<NAME>_RULES = [
    Rule("char_limit", lambda c: len(c) <= <LIMIT>),
    Rule("has_hook_in_first_line", lambda c: bool(c.split("\n")[0].strip())),
    # ...add platform-specific rules
]
```

### 4. Cascade entry

Edit `backend/app/llm/cascade.py`. Add to `CASCADES`:

```python
"<name>_gen": [
    "groq/llama-3.3-70b-versatile",  # tier 1
    "groq/openai/gpt-oss-120b",      # tier 2
    "anthropic/claude-sonnet-4-6",   # tier 3 (failsafe)
],
```

For short-form platforms, swap tier 3 to `claude-haiku-4-5` to save cost.

### 5. Wire into LangGraph

Edit `backend/app/graph/builder.py`. In the fan-out section:

```python
if "<name>" in state["selected_platforms"]:
    tasks.append(<Name>Generator().generate(state))
```

### 6. Test scaffold

Create `backend/tests/generators/test_<name>.py` with:
- Smoke test (generates without error)
- Adherence test (output passes all rules)
- Cascade fallthrough test (mock Tier 1 failure, assert Tier 2 used)

## Verification

After creation:
1. Run `uv run pytest backend/tests/generators/test_<name>.py` — must pass
2. Run a real generation via the UI — manually inspect output for voice + format
3. Run `uv run python bench/runner.py --platforms <name>` to add to bench
4. Add `<name>` to `frontend/src/lib/platforms.ts` so it appears in the compose UI checkboxes

## Common mistakes

- Putting cascade config inline in the generator class (always in `cascade.py`)
- Hardcoding example posts in code (always in the markdown prompt file)
- Forgetting to add the platform to `frontend/src/lib/platforms.ts` — backend works, UI never shows it
- Writing adherence rules that LLM-judge subjectively ("is the hook good?"). Adherence rules must be deterministic Python. Subjective scoring goes in `evals/llm_judge.py`.