<script lang="ts">
	import { listDrafts, scheduleDraft, type SavedDraft } from '$lib/api';
	import { onMount } from 'svelte';

	const BASE = 'http://localhost:8000/api';

	let drafts = $state<SavedDraft[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let approving = $state<Record<number, boolean>>({});
	let scheduling = $state<Record<number, boolean>>({});
	let scheduleTime = $state<Record<number, string>>({});

	onMount(async () => {
		try {
			drafts = await listDrafts();
			// Default schedule time for each draft: 2 min from now
			const base = new Date(Date.now() + 2 * 60 * 1000);
			const defaultVal = toLocalDatetimeInput(base);
			drafts.forEach((d) => {
				if (d.status !== 'scheduled') scheduleTime[d.id] = defaultVal;
			});
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	function toLocalDatetimeInput(d: Date): string {
		const pad = (n: number) => String(n).padStart(2, '0');
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

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
				d.id === id ? { ...d, status: 'scheduled', scheduled_at: dt.toISOString() } : d
			);
		} catch (e) {
			alert((e as Error).message);
		} finally {
			scheduling = { ...scheduling, [id]: false };
		}
	}

	function formatDate(iso: string) {
		return new Date(iso).toLocaleString();
	}

	function statusColor(status: string) {
		return status === 'approved' ? 'green' : status === 'scheduled' ? 'amber' : 'neutral';
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
			<div class="card" class:approved={draft.status === 'approved'} class:scheduled={draft.status === 'scheduled'}>
				<div class="card-header">
					<span class="platform">{draft.platform}</span>
					<div class="header-right">
						<span class="meta">{formatDate(draft.created_at)} · ${draft.total_cost_usd.toFixed(6)}</span>
						<span class="badge badge-{statusColor(draft.status)}">{draft.status}</span>
					</div>
				</div>

				<pre class="content">{draft.content}</pre>
				<p class="ctx">Context: {draft.context_input.slice(0, 120)}{draft.context_input.length > 120 ? '…' : ''}</p>

				<div class="actions">
					{#if draft.status === 'scheduled' && draft.scheduled_at}
						<span class="scheduled-info">Scheduled for {formatDate(draft.scheduled_at)}</span>
					{:else}
						{#if draft.status !== 'approved'}
							<button
								class="btn btn-approve"
								disabled={approving[draft.id]}
								onclick={() => approve(draft.id)}
							>
								{approving[draft.id] ? 'Approving…' : 'Approve'}
							</button>
						{/if}

						<div class="schedule-row">
							<input
								type="datetime-local"
								bind:value={scheduleTime[draft.id]}
								class="dt-input"
							/>
							<button
								class="btn btn-schedule"
								disabled={scheduling[draft.id] || !scheduleTime[draft.id]}
								onclick={() => schedule(draft.id)}
							>
								{scheduling[draft.id] ? 'Scheduling…' : 'Schedule'}
							</button>
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

	.card {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		overflow: hidden;
		transition: border-color 0.2s;
	}
	.card.approved { border-color: #166534; }
	.card.scheduled { border-color: #92400e; }

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.6rem 1rem;
		background: #222;
		border-bottom: 1px solid #2a2a2a;
		gap: 1rem;
	}

	.header-right { display: flex; align-items: center; gap: 0.75rem; }

	.platform {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #60a5fa;
	}

	.meta { font-size: 0.75rem; color: #6b7280; }

	.badge {
		font-size: 0.7rem;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-weight: 600;
	}
	.badge-green { background: #14532d; color: #4ade80; }
	.badge-amber { background: #451a03; color: #fbbf24; }
	.badge-neutral { background: #1f2937; color: #9ca3af; }

	.content {
		padding: 1rem;
		margin: 0;
		white-space: pre-wrap;
		font-family: inherit;
		font-size: 0.9rem;
		line-height: 1.6;
		color: #e5e5e5;
	}

	.ctx {
		padding: 0 1rem 0;
		margin: 0;
		font-size: 0.75rem;
		color: #4b5563;
	}

	.actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-top: 1px solid #2a2a2a;
		flex-wrap: wrap;
	}

	.schedule-row { display: flex; align-items: center; gap: 0.5rem; }

	.dt-input {
		background: #111;
		border: 1px solid #374151;
		border-radius: 4px;
		color: #e5e5e5;
		font-size: 0.8rem;
		padding: 0.25rem 0.5rem;
		color-scheme: dark;
	}

	.btn {
		padding: 0.25rem 0.75rem;
		border: none;
		border-radius: 4px;
		font-size: 0.8rem;
		cursor: pointer;
		white-space: nowrap;
	}
	.btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.btn-approve { background: #166534; color: #4ade80; }
	.btn-approve:hover:not(:disabled) { background: #15803d; }
	.btn-schedule { background: #1d4ed8; color: #fff; }
	.btn-schedule:hover:not(:disabled) { background: #1e40af; }

	.scheduled-info { font-size: 0.8rem; color: #fbbf24; }
</style>
