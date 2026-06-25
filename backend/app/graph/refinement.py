"""
Refinement subgraph.

Separate from the main generation graph — does not re-run router, research,
or style memory. Takes an existing draft and a free-text instruction, returns
a revised draft persisted as a new DraftRevision row.

Public API
----------
  refine(draft_id, instruction)
      → {"revision": dict, "warning": None | "soft_limit_reached"}

  revert_to_revision(draft_id, revision_number)
      → dict  (the newly-activated revision)
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.db.models import Draft, DraftRevision
from app.db.session import SessionLocal
from app.evals.adherence.by_type import check_by_type
from app.graph.nodes.adherence import _check_linkedin, _check_medium, _check_x
from app.llm.cascade import CASCADES, call
from app.llm.post_types import ALLOWED_TYPES, DEFAULT_TYPE
from app.llm.prompts import load

log = logging.getLogger(__name__)

# Refinements beyond this number trigger a soft-limit warning in the response.
MAX_REFINEMENTS_BEFORE_WARNING = 3

_PLATFORM_CHECKERS = {
    "linkedin": _check_linkedin,
    "x":        _check_x,
    "medium":   _check_medium,
}


# ---------------------------------------------------------------------------
# Internal context dataclass
# ---------------------------------------------------------------------------

@dataclass
class _Ctx:
    draft_id: int
    platform: str
    post_type: str
    mode: str               # quality mode inferred from model_used
    start_tier: int         # cascade tier index to start from
    context_input: str
    current_content: str
    current_revision_number: int
    past_instructions: list[str] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_mode_and_tier(model_used: str, platform: str) -> tuple[str, int]:
    """
    Reverse-lookup the (mode, tier_index) for a stored model name.

    Checks in preference order so that a model that appears in multiple modes
    (e.g. llama-3.3-70b is both balanced/0 and fast/1) resolves to the
    highest-quality mode it belongs to.
    Falls back to ("balanced", 0) if the model isn't in any cascade.
    """
    cascade = CASCADES.get(platform, CASCADES["linkedin"])
    for preferred_mode in ("balanced", "polish", "fast"):
        tier_list = cascade.get(preferred_mode, [])
        for i, m in enumerate(tier_list):
            if m == model_used:
                return preferred_mode, i
    return "balanced", 0


def _load_context(draft_id: int) -> _Ctx:
    with SessionLocal() as db:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        current_rev = (
            db.query(DraftRevision)
            .filter(
                DraftRevision.draft_id == draft_id,
                DraftRevision.is_current == True,  # noqa: E712
            )
            .first()
        )
        if not current_rev:
            raise ValueError(f"No current revision for draft {draft_id}")

        past_revs = (
            db.query(DraftRevision)
            .filter(
                DraftRevision.draft_id == draft_id,
                DraftRevision.refinement_instruction.isnot(None),
            )
            .order_by(DraftRevision.revision_number)
            .all()
        )
        past_instructions = [r.refinement_instruction for r in past_revs if r.refinement_instruction]

        # Infer cascade mode + start tier from the model that generated this draft.
        model_used = current_rev.model_used or ""
        platform = draft.platform or "linkedin"
        mode, start_tier = _infer_mode_and_tier(model_used, platform)

        # If model_tier was explicitly stored on the draft, prefer it.
        if draft.model_tier is not None:
            start_tier = draft.model_tier

        post_type = draft.post_type or DEFAULT_TYPE.get(platform, "")

        return _Ctx(
            draft_id=draft_id,
            platform=platform,
            post_type=post_type,
            mode=mode,
            start_tier=start_tier,
            context_input=draft.context_input or "",
            current_content=current_rev.content,
            current_revision_number=current_rev.revision_number,
            past_instructions=past_instructions,
        )


def _prompt_path(platform: str, post_type: str) -> str:
    if post_type in ALLOWED_TYPES.get(platform, []):
        return f"{platform}/{post_type}.md"
    fallback = DEFAULT_TYPE.get(platform, "")
    return f"{platform}/{fallback}.md" if fallback else f"{platform}_gen.md"


def _build_user_message(ctx: _Ctx, instruction: str) -> str:
    past_block = (
        "\n".join(f"- {i}" for i in ctx.past_instructions)
        if ctx.past_instructions
        else "none"
    )
    return (
        f"You previously generated this draft for {ctx.platform}:\n\n"
        f"{ctx.current_content}\n\n"
        f'The user wants this changed:\n"{instruction}"\n\n'
        f"Context for this draft:\n{ctx.context_input}\n\n"
        f"Past refinements applied to this draft (for context only):\n{past_block}\n\n"
        "Refinement rules:\n"
        "1. Preserve everything the user did not ask to change.\n"
        "2. Make ONLY the requested change. Do not take other liberties on tone, length, or structure.\n"
        f"3. Keep the same post type structure ({ctx.post_type}) and voice.\n"
        "4. Return the full revised draft, not a diff.\n"
        "5. Do not add commentary, preamble, or explanation.\n\n"
        "Output only the revised draft text."
    )


def _all_issues(platform: str, post_type: str, content: str) -> list[str]:
    issues: list[str] = []
    checker = _PLATFORM_CHECKERS.get(platform)
    if checker:
        issues.extend(checker(content))
    issues.extend(check_by_type(platform, post_type, content))
    return issues


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def refine(draft_id: int, instruction: str) -> dict:
    """
    Refinement subgraph entry point.

    Returns
    -------
    {
        "revision": {id, draft_id, revision_number, content, ...},
        "warning": None | "soft_limit_reached",
    }
    """
    ctx = _load_context(draft_id)

    messages = [
        {"role": "system", "content": load(_prompt_path(ctx.platform, ctx.post_type))},
        {"role": "user",   "content": _build_user_message(ctx, instruction)},
    ]

    # --- LLM call with tier inheritance ---
    t0 = time.perf_counter()
    with SessionLocal() as db:
        content, meta = await call(
            f"{ctx.platform}_refine",
            ctx.platform,
            messages,
            ctx.run_id,
            db,
            mode=ctx.mode,
            start_tier=ctx.start_tier,
        )
    latency_ms = int((time.perf_counter() - t0) * 1000)

    # --- Adherence check + one retry ---
    issues = _all_issues(ctx.platform, ctx.post_type, content)
    adherence_passed = not issues

    if not adherence_passed:
        retry_messages = messages + [
            {"role": "assistant", "content": content},
            {
                "role": "user",
                "content": (
                    "That draft has these issues:\n"
                    + "\n".join(f"- {i}" for i in issues)
                    + "\n\nPlease fix them and rewrite."
                ),
            },
        ]
        try:
            with SessionLocal() as db:
                content_retry, meta_retry = await call(
                    f"{ctx.platform}_refine_retry",
                    ctx.platform,
                    retry_messages,
                    ctx.run_id,
                    db,
                    mode=ctx.mode,
                    start_tier=ctx.start_tier,
                )
            remaining = _all_issues(ctx.platform, ctx.post_type, content_retry)
            content = content_retry
            meta = meta_retry
            adherence_passed = not remaining
            issues = remaining
        except Exception as exc:
            log.warning("refinement: adherence retry failed (%s), keeping first attempt", exc)

    # --- Persist revision (is_current swap + draft.content update, one transaction) ---
    new_revision_number = ctx.current_revision_number + 1
    revision_id = f"r{new_revision_number}-{ctx.draft_id}-{ctx.run_id[:8]}"

    with SessionLocal() as db:
        db.query(DraftRevision).filter(
            DraftRevision.draft_id == ctx.draft_id,
        ).update({"is_current": False}, synchronize_session=False)

        new_rev = DraftRevision(
            id=revision_id,
            draft_id=ctx.draft_id,
            revision_number=new_revision_number,
            content=content,
            refinement_instruction=instruction,
            model_used=meta.get("model", "unknown"),
            tier=meta.get("tier", ctx.start_tier),
            tokens_in=meta.get("prompt_tokens"),
            tokens_out=meta.get("completion_tokens"),
            cost_usd=meta.get("cost_usd"),
            latency_ms=latency_ms,
            adherence_passed=adherence_passed,
            adherence_failures=json.dumps(issues) if issues else None,
            is_current=True,
            created_at=datetime.utcnow(),
        )
        db.add(new_rev)

        draft = db.query(Draft).filter(Draft.id == ctx.draft_id).first()
        if draft:
            draft.content = content

        db.commit()

    warning = (
        "soft_limit_reached"
        if new_revision_number > MAX_REFINEMENTS_BEFORE_WARNING
        else None
    )

    return {
        "revision": {
            "id": revision_id,
            "draft_id": ctx.draft_id,
            "revision_number": new_revision_number,
            "content": content,
            "refinement_instruction": instruction,
            "model_used": meta.get("model", "unknown"),
            "tier": meta.get("tier", ctx.start_tier),
            "tokens_in": meta.get("prompt_tokens"),
            "tokens_out": meta.get("completion_tokens"),
            "cost_usd": meta.get("cost_usd"),
            "latency_ms": latency_ms,
            "adherence_passed": adherence_passed,
            "adherence_failures": issues,
            "is_current": True,
            "created_at": datetime.utcnow().isoformat(),
        },
        "warning": warning,
    }


def revert_to_revision(draft_id: int, revision_number: int) -> dict:
    """
    Flip the is_current flag to the requested revision and update draft.content.
    No LLM call. Returns the newly-activated revision as a dict.
    """
    with SessionLocal() as db:
        target = (
            db.query(DraftRevision)
            .filter(
                DraftRevision.draft_id == draft_id,
                DraftRevision.revision_number == revision_number,
            )
            .first()
        )
        if not target:
            raise ValueError(
                f"Revision {revision_number} not found for draft {draft_id}"
            )

        db.query(DraftRevision).filter(
            DraftRevision.draft_id == draft_id,
        ).update({"is_current": False}, synchronize_session=False)

        target.is_current = True

        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if draft:
            draft.content = target.content

        db.commit()
        db.refresh(target)

        return {
            "id": target.id,
            "draft_id": target.draft_id,
            "revision_number": target.revision_number,
            "content": target.content,
            "refinement_instruction": target.refinement_instruction,
            "model_used": target.model_used,
            "tier": target.tier,
            "is_current": target.is_current,
            "created_at": target.created_at.isoformat(),
        }
