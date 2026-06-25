<script lang="ts">
	import {
		listDrafts,
		listRevisions,
		scheduleDraft,
		regenerateDraft,
		refineInstruction,
		revertRevision,
		type SavedDraft,
		type Revision,
	} from '$lib/api';
	import { onMount } from 'svelte';

	const BASE = 'http://localhost:8000/api';
	const MAX_REFINEMENTS = 3;

	// Mirror of backend ALLOWED_TYPES — locked per brief.
	const PLATFORM_TYPES: Record<string, string[]> = {
		linkedin: ['project_showcase', 'technical_deep_dive', 'learning', 'event_recap', 'hot_take', 'milestone'],
		x: ['thread', 'single_shot', 'hot_take', 'link_share', 'live_event'],
		medium: ['tutorial', 'case_study', 'opinion', 'deep_analysis'],
	};

	// ── Core state ──────────────────────────────────────────────────────────
	let drafts = $state<SavedDraft[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Per-draft action state ───────────────────────────────────────────────
	let approving      = $state<Record<number, boolean>>({});
	let scheduling     = $state<Record<number, boolean>>({});
	let regenerating   = $state<Record<number, boolean>>({});
	let refining       = $state<Record<number, boolean>>({});
	let reverting      = $state<Record<number, boolean>>({});
	let scheduleTime   = $state<Record<number, string>>({});
	let refineInput    = $state<Record<number, string>>({});

	// ── Revision history (loaded per-draft at mount) ─────────────────────────
	let revisions      = $state<Record<number, Revision[]>>({});
	let softLimitHit   = $state<Record<number, boolean>>({});

	// ── Lifecycle ────────────────────────────────────────────────────────────
	onMount(async () => {
		try {
			drafts = await listDrafts();
			const base = new Date(Date.now() + 2 * 60 * 1000);
			const defaultVal = toLocalDatetimeInput(base);
			drafts.forEach((d) => {
				if (d.status !== 'scheduled') scheduleTime[d.id] = defaultVal;
			});

			// Load revision history for all drafts in parallel (fast DB reads).
			await Promise.all(
				drafts.map(async (d) => {
					try {
						const data = await listRevisions(d.id);
						revisions = { ...revisions, [d.id]: data.revisions };
					} catch {
						// Non-fatal: revision history just won't show for this draft.
					}
				}),
			);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	// ── Helpers ──────────────────────────────────────────────────────────────
	function toLocalDatetimeInput(d: Date): string {
		const pad = (n: number) => String(n).padStart(2, '0');
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

	function formatType(t: string): string {
		return t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	function parsePostTypesJson(raw: string | null): { reasoning: string } {
		if (!raw) return { reasoning: '' };
		try {
			const parsed = JSON.parse(raw);
			return { reasoning: parsed.__reasoning__ ?? '' };
		} catch {
			return { reasoning: '' };
		}
	}

	function currentRevNum(draftId: number): number {
		return revisions[draftId]?.find((r) => r.is_current)?.revision_number ?? 0;
	}

	function formatDate(iso: string) {
		return new Date(iso).toLocaleString();
	}

	function statusColor(status: string) {
		return status === 'approved' ? 'green' : status === 'scheduled' ? 'amber' : 'neutral';
	}

	// ── Actions ──────────────────────────────────────────────────────────────
	async function approve(id: number) {
		approving = { ...approving, [id]: true };
		try {
			const res = await fetch(`${BASE}/drafts/${id}/approve`, { method: 'POST' });
			if (!res.ok) throw new Error('Approve failed');
			drafts = drafts.map((d) => (d.id === id ? { ...d, status: 'approved' } : d));
		} catch (e) {
			alert((e as Error).message);
		} finally {
			approving = { ...approving, [id]: false };
		}
	}

	async function schedule(id: number) {
		const val = scheduleTime[id];
		if (!val) return;
		scheduling = { ...scheduling, [id]: true };
		try {
			const dt = new Date(val);
			await scheduleDraft(id, dt);
			drafts = drafts.map((d) =>
				d.id === id ? { ...d, status: 'scheduled', scheduled_at: dt.toISOString() } : d,
			);
		} catch (e) {
			alert((e as Error).message);
		} finally {
			scheduling = { ...scheduling, [id]: false };
		}
	}

	async function changeType(draft: SavedDraft, newType: string) {
		if (newType === draft.post_type) return;
		regenerating = { ...regenerating, [draft.id]: true };
		try {
			const updated = await regenerateDraft(draft.id, draft.platform, newType);
			drafts = drafts.map((d) => (d.id === draft.id ? { ...d, ...updated } : d));
		} catch (e) {
			alert(`Regenerate failed: ${(e as Error).message}`);
		} finally {
			regenerating = { ...regenerating, [draft.id]: false };
		}
	}

	async function sendRefinement(draft: SavedDraft) {
		const instruction = refineInput[draft.id]?.trim();
		if (!instruction) return;
		refining = { ...refining, [draft.id]: true };
		try {
			const result = await refineInstruction(draft.id, instruction);

			// Update displayed content
			drafts = drafts.map((d) =>
				d.id === draft.id ? { ...d, content: result.revision.content } : d,
			);

			// Append new revision to local history
			const prev = (revisions[draft.id] ?? []).map((r) => ({ ...r, is_current: false }));
			revisions = { ...revisions, [draft.id]: [...prev, result.revision] };

			// Track soft limit
			if (result.warning === 'soft_limit_reached') {
				softLimitHit = { ...softLimitHit, [draft.id]: true };
			}

			// Clear input
			refineInput = { ...refineInput, [draft.id]: '' };
		} catch (e) {
			alert(`Refinement failed: ${(e as Error).message}`);
		} finally {
			refining = { ...refining, [draft.id]: false };
		}
	}

	async function revert(draftId: number, revisionNumber: number) {
		reverting = { ...reverting, [draftId]: true };
		try {
			const result = await revertRevision(draftId, revisionNumber);

			// Update displayed content
			drafts = drafts.map((d) =>
				d.id === draftId ? { ...d, content: result.current_revision.content } : d,
			);

			// Flip is_current flags locally
			revisions = {
				...revisions,
				[draftId]: (revisions[draftId] ?? []).map((r) => ({
					...r,
					is_current: r.revision_number === revisionNumber,
				})),
			};
		} catch (e) {
			alert(`Revert failed: ${(e as Error).message}`);
		} finally {
			reverting = { ...reverting, [draftId]: false };
		}
	}
</script>

<div class="page">
	<h1>Drafts</h1>
	<p class="subtitle">Review, approve, and schedule your generated drafts.</p>

	{#if loading}
		<p class="muted">Loading...</p>
	{:else if error}
		<p class="err">{error}</p>
	{:else if drafts.length === 0}
		<p class="muted">No drafts yet. Generate some from the Compose page.</p>
	{:else}
		{#each drafts as draft}
			{@const { reasoning } = parsePostTypesJson(draft.post_types_json)}
			{@const types = PLATFORM_TYPES[draft.platform] ?? []}
			{@const draftRevisions = revisions[draft.id] ?? []}
			{@const revNum = currentRevNum(draft.id)}

			<div class="card" class:approved={draft.status === 'approved'} class:scheduled={draft.status === 'scheduled'}>

				<!-- ── Card header: platform + type selector + meta ── -->
				<div class="card-header">
					<div class="header-left">
						<span class="platform">{draft.platform}</span>

						{#if types.length > 0}
							<div class="type-row">
								<select
									class="type-select"
									disabled={regenerating[draft.id]}
									value={draft.post_type ?? types[0]}
									onchange={(e) => changeType(draft, (e.target as HTMLSelectElement).value)}
								>
									{#each types as t}
										<option value={t}>{formatType(t)}</option>
									{/each}
								</select>

								{#if reasoning}
									<span class="tooltip-anchor">
										<span class="tooltip-icon">ⓘ</span>
										<span class="tooltip-text">{reasoning}</span>
									</span>
								{/if}
							</div>
						{/if}
					</div>

					<div class="header-right">
						<span class="meta">{formatDate(draft.created_at)} · ${draft.total_cost_usd.toFixed(6)}</span>
						<span class="badge badge-{statusColor(draft.status)}">{draft.status}</span>
					</div>
				</div>

				<!-- ── Content area ── -->
				<div class="content-wrap" class:is-regenerating={regenerating[draft.id]}>
					{#if regenerating[draft.id]}
						<div class="regen-overlay">
							<span class="spinner"></span>
							<span class="regen-label">Regenerating…</span>
						</div>
					{/if}
					<pre class="content">{draft.content}</pre>
				</div>

				<p class="ctx">Context: {draft.context_input.slice(0, 120)}{draft.context_input.length > 120 ? '…' : ''}</p>

				<!-- ── Approve / Schedule actions ── -->
				<div class="actions">
					{#if draft.status === 'scheduled' && draft.scheduled_at}
						<span class="scheduled-info">Scheduled for {formatDate(draft.scheduled_at)}</span>
					{:else}
						{#if draft.status !== 'approved'}
							<button
								class="btn btn-approve"
								disabled={approving[draft.id] || regenerating[draft.id] || refining[draft.id]}
								onclick={() => approve(draft.id)}
							>
								{approving[draft.id] ? 'Approving…' : 'Approve & Save Voice'}
							</button>
						{/if}

						<div class="schedule-row">
							<input
								type="datetime-local"
								bind:value={scheduleTime[draft.id]}
								class="dt-input"
								disabled={regenerating[draft.id] || refining[draft.id]}
							/>
							<button
								class="btn btn-schedule"
								disabled={scheduling[draft.id] || !scheduleTime[draft.id] || regenerating[draft.id] || refining[draft.id]}
								onclick={() => schedule(draft.id)}
							>
								{scheduling[draft.id] ? 'Scheduling…' : 'Schedule'}
							</button>
						</div>
					{/if}
				</div>

				<!-- ── Refinement panel ── -->
				<div class="refine-panel">

					{#if revNum > 0}
						<div class="revision-counter">Revision {revNum}</div>
					{/if}

					{#if softLimitHit[draft.id]}
						<div class="soft-limit-warning">
							⚠️ You've used {MAX_REFINEMENTS} refinements. Drafts often drift after this point.
							<a href="/" class="discard-link">Discard &amp; start fresh</a>
						</div>
					{/if}

					<div class="refine-input-row">
						<input
							class="refine-input"
							type="text"
							placeholder='e.g. "Make paragraph 3 less salesy"'
							value={refineInput[draft.id] ?? ''}
							disabled={refining[draft.id]}
							oninput={(e) => { refineInput = { ...refineInput, [draft.id]: (e.target as HTMLInputElement).value }; }}
							onkeydown={(e) => { if (e.key === 'Enter') sendRefinement(draft); }}
						/>
						<button
							class="btn btn-refine"
							disabled={refining[draft.id] || !(refineInput[draft.id]?.trim())}
							onclick={() => sendRefinement(draft)}
						>
							{#if refining[draft.id]}
								<span class="spinner spinner-sm"></span>
							{:else}
								Send
							{/if}
						</button>
					</div>

					<p class="refine-tip">ⓘ Tip: be specific — "Make paragraph 3 less salesy" works better than "make it better"</p>

					{#if draftRevisions.length > 1}
						<div class="history-strip">
							<span class="history-label">History:</span>
							{#each draftRevisions as rev}
								<span class="tooltip-anchor">
									<button
										class="history-btn"
										class:is-current={rev.is_current}
										disabled={reverting[draft.id] || rev.is_current}
										onclick={() => revert(draft.id, rev.revision_number)}
									>
										v{rev.revision_number}{rev.is_current ? ' ←' : ''}
									</button>
									{#if rev.refinement_instruction}
										<span class="tooltip-text tooltip-above">{rev.refinement_instruction}</span>
									{/if}
								</span>
							{/each}
						</div>
					{/if}

				</div>
			</div>
		{/each}
	{/if}
</div>

<style>
	.page { display: flex; flex-direction: column; gap: 1rem; }
	h1 { font-size: 1.5rem; font-weight: 600; }
	.subtitle { color: #a3a3a3; font-size: 0.9rem; }
	.muted { color: #6b7280; font-size: 0.9rem; }
	.err { color: #f87171; font-size: 0.9rem; }

	/* ── Card ── */
	.card {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		overflow: hidden;
		transition: border-color 0.2s;
	}
	.card.approved { border-color: #166534; }
	.card.scheduled { border-color: #92400e; }

	/* ── Header ── */
	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.6rem 1rem;
		background: #222;
		border-bottom: 1px solid #2a2a2a;
		gap: 1rem;
		flex-wrap: wrap;
	}
	.header-left { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
	.header-right { display: flex; align-items: center; gap: 0.75rem; }
	.platform {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #60a5fa;
		white-space: nowrap;
	}
	.meta { font-size: 0.75rem; color: #6b7280; }

	/* ── Type selector ── */
	.type-row { display: flex; align-items: center; gap: 0.4rem; }
	.type-select {
		background: #111;
		border: 1px solid #374151;
		border-radius: 4px;
		color: #d1d5db;
		font-size: 0.75rem;
		padding: 0.2rem 0.4rem;
		cursor: pointer;
	}
	.type-select:disabled { opacity: 0.5; cursor: not-allowed; }
	.type-select:hover:not(:disabled) { border-color: #60a5fa; }

	/* ── Tooltip ── */
	.tooltip-anchor { position: relative; display: inline-flex; align-items: center; }
	.tooltip-icon { font-size: 0.8rem; color: #6b7280; cursor: default; user-select: none; }
	.tooltip-anchor:hover .tooltip-icon { color: #9ca3af; }
	.tooltip-text {
		display: none;
		position: absolute;
		top: calc(100% + 6px);
		left: 0;
		min-width: 200px;
		max-width: 320px;
		background: #111;
		border: 1px solid #374151;
		border-radius: 6px;
		padding: 0.4rem 0.6rem;
		font-size: 0.75rem;
		color: #d1d5db;
		line-height: 1.5;
		z-index: 20;
		white-space: normal;
		word-break: break-word;
	}
	.tooltip-text.tooltip-above {
		top: auto;
		bottom: calc(100% + 6px);
	}
	.tooltip-anchor:hover .tooltip-text { display: block; }

	/* ── Badges ── */
	.badge { font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; }
	.badge-green { background: #14532d; color: #4ade80; }
	.badge-amber { background: #451a03; color: #fbbf24; }
	.badge-neutral { background: #1f2937; color: #9ca3af; }

	/* ── Content ── */
	.content-wrap { position: relative; }
	.content-wrap.is-regenerating { opacity: 0.4; pointer-events: none; }
	.regen-overlay {
		position: absolute; inset: 0;
		display: flex; align-items: center; justify-content: center; gap: 0.5rem;
		background: rgba(0,0,0,0.5); z-index: 10;
	}
	.regen-label { font-size: 0.8rem; color: #9ca3af; }
	.content {
		padding: 1rem; margin: 0;
		white-space: pre-wrap;
		font-family: inherit; font-size: 0.9rem; line-height: 1.6; color: #e5e5e5;
	}
	.ctx { padding: 0 1rem; margin: 0; font-size: 0.75rem; color: #4b5563; }

	/* ── Actions ── */
	.actions {
		display: flex; align-items: center; gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-top: 1px solid #2a2a2a;
		flex-wrap: wrap;
	}
	.schedule-row { display: flex; align-items: center; gap: 0.5rem; }
	.dt-input {
		background: #111; border: 1px solid #374151; border-radius: 4px;
		color: #e5e5e5; font-size: 0.8rem; padding: 0.25rem 0.5rem; color-scheme: dark;
	}
	.dt-input:disabled { opacity: 0.5; }
	.scheduled-info { font-size: 0.8rem; color: #fbbf24; }

	/* ── Buttons ── */
	.btn {
		padding: 0.25rem 0.75rem; border: none; border-radius: 4px;
		font-size: 0.8rem; cursor: pointer; white-space: nowrap;
		display: inline-flex; align-items: center; gap: 0.4rem;
	}
	.btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.btn-approve { background: #166534; color: #4ade80; }
	.btn-approve:hover:not(:disabled) { background: #15803d; }
	.btn-schedule { background: #1d4ed8; color: #fff; }
	.btn-schedule:hover:not(:disabled) { background: #1e40af; }
	.btn-refine { background: #374151; color: #e5e5e5; }
	.btn-refine:hover:not(:disabled) { background: #4b5563; }

	/* ── Spinner ── */
	.spinner {
		width: 16px; height: 16px;
		border: 2px solid #374151; border-top-color: #60a5fa;
		border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block;
	}
	.spinner-sm { width: 12px; height: 12px; }
	@keyframes spin { to { transform: rotate(360deg); } }

	/* ── Refinement panel ── */
	.refine-panel {
		border-top: 1px solid #1f2937;
		padding: 0.75rem 1rem 0.6rem;
		display: flex; flex-direction: column; gap: 0.5rem;
		background: #161616;
	}

	.revision-counter { font-size: 0.75rem; color: #6b7280; }

	.soft-limit-warning {
		background: #1c1207;
		border: 1px solid #78350f;
		border-radius: 6px;
		padding: 0.4rem 0.6rem;
		font-size: 0.78rem;
		color: #fbbf24;
		display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
	}
	.discard-link { color: #60a5fa; font-size: 0.78rem; text-decoration: underline; }

	.refine-input-row { display: flex; gap: 0.5rem; align-items: center; }
	.refine-input {
		flex: 1;
		background: #111; border: 1px solid #374151; border-radius: 4px;
		color: #e5e5e5; font-size: 0.82rem; padding: 0.3rem 0.5rem;
		min-width: 0;
	}
	.refine-input:focus { outline: none; border-color: #60a5fa; }
	.refine-input:disabled { opacity: 0.5; }

	.refine-tip { font-size: 0.72rem; color: #4b5563; margin: 0; }

	/* ── History strip ── */
	.history-strip {
		display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap;
	}
	.history-label { font-size: 0.72rem; color: #6b7280; margin-right: 0.15rem; }
	.history-btn {
		background: #1f2937; border: 1px solid #374151; border-radius: 4px;
		color: #9ca3af; font-size: 0.72rem; padding: 0.15rem 0.4rem;
		cursor: pointer; white-space: nowrap;
	}
	.history-btn:hover:not(:disabled) { border-color: #60a5fa; color: #e5e5e5; }
	.history-btn:disabled { cursor: default; }
	.history-btn.is-current {
		background: #1e3a5f; border-color: #3b82f6; color: #93c5fd;
	}
</style>
