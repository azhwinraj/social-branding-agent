<script lang="ts">
	import { listDrafts, type SavedDraft } from '$lib/api';
	import { onMount } from 'svelte';

	let drafts = $state<SavedDraft[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			drafts = await listDrafts();
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	function formatDate(iso: string) {
		return new Date(iso).toLocaleString();
	}
</script>

<div class="page">
	<h1>Drafts</h1>
	<p class="subtitle">All generated drafts pending your review.</p>

	{#if loading}
		<p class="muted">Loading...</p>
	{:else if error}
		<p class="err">{error}</p>
	{:else if drafts.length === 0}
		<p class="muted">No drafts yet. Generate some from the Compose page.</p>
	{:else}
		{#each drafts as draft}
			<div class="card">
				<div class="card-header">
					<span class="platform">{draft.platform}</span>
					<span class="meta">
						{formatDate(draft.created_at)} · ${draft.total_cost_usd.toFixed(6)} · <span class="status">{draft.status}</span>
					</span>
				</div>
				<pre class="content">{draft.content}</pre>
				<p class="ctx">Context: {draft.context_input.slice(0, 120)}{draft.context_input.length > 120 ? '…' : ''}</p>
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
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.6rem 1rem;
		background: #222;
		border-bottom: 1px solid #2a2a2a;
	}

	.platform {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #60a5fa;
	}

	.meta { font-size: 0.75rem; color: #6b7280; }
	.status { color: #fbbf24; }

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
		padding: 0 1rem 0.75rem;
		margin: 0;
		font-size: 0.75rem;
		color: #4b5563;
	}
</style>
