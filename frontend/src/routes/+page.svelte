<script lang="ts">
	import { healthCheck, generate } from '$lib/api';
	import { onMount } from 'svelte';

	interface Draft {
		platform: string;
		content: string;
		model: string;
		prompt_tokens: number;
		completion_tokens: number;
		cost_usd: number;
		adherence_warning?: boolean;
	}

	let backendStatus = $state<'checking' | 'ok' | 'error'>('checking');
	let context = $state('');
	let platforms = $state(['linkedin', 'x', 'medium']);
	let loading = $state(false);
	let drafts = $state<Draft[]>([]);
	let error = $state<string | null>(null);
	let runId = $state<string | null>(null);
	let imageDescription = $state<string | null>(null);

	function handleImageChange(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (file) {
			const mb = (file.size / 1024 / 1024).toFixed(1);
			imageDescription = `${file.name} (${mb} MB)`;
		} else {
			imageDescription = null;
		}
	}

	onMount(async () => {
		try {
			await healthCheck();
			backendStatus = 'ok';
		} catch {
			backendStatus = 'error';
		}
	});

	async function handleGenerate() {
		if (!context.trim()) return;
		loading = true;
		drafts = [];
		error = null;
		runId = null;
		try {
			const data = await generate(context, platforms, imageDescription ?? undefined);
			drafts = data.drafts;
			runId = data.run_id;
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}

	function totalCost(ds: Draft[]) {
		return ds.reduce((s, d) => s + d.cost_usd, 0);
	}

	function totalTokens(ds: Draft[]) {
		return ds.reduce((s, d) => s + d.prompt_tokens + d.completion_tokens, 0);
	}
</script>

<div class="page">
	<div class="status" class:ok={backendStatus === 'ok'} class:error={backendStatus === 'error'}>
		Backend: {backendStatus === 'checking' ? 'connecting...' : backendStatus === 'ok' ? 'connected' : 'unreachable'}
	</div>

	<h1>Compose</h1>
	<p class="subtitle">Paste your context and get platform-specific drafts.</p>

	<textarea
		bind:value={context}
		placeholder="What do you want to post about?"
		rows={6}
	></textarea>

	<label class="image-label">
		<span>Attach image (optional)</span>
		<input type="file" accept="image/*" onchange={handleImageChange} />
		{#if imageDescription}<span class="image-name">{imageDescription}</span>{/if}
	</label>

	<div class="platforms">
		{#each ['linkedin', 'x', 'medium'] as p}
			<label>
				<input
					type="checkbox"
					checked={platforms.includes(p)}
					onchange={(e) => {
						if ((e.target as HTMLInputElement).checked) {
							platforms = [...platforms, p];
						} else {
							platforms = platforms.filter((x) => x !== p);
						}
					}}
				/>
				{p.charAt(0).toUpperCase() + p.slice(1)}
			</label>
		{/each}
	</div>

	<button onclick={handleGenerate} disabled={loading || !context.trim()}>
		{loading ? 'Generating...' : 'Generate Drafts'}
	</button>

	{#if error}
		<div class="error-box">{error}</div>
	{/if}

	{#if drafts.length > 0}
		<div class="meta-row">
			<span>{drafts.length} draft{drafts.length > 1 ? 's' : ''}</span>
			<span>{totalTokens(drafts).toLocaleString()} tokens</span>
			<span>${totalCost(drafts).toFixed(6)}</span>
			{#if runId}<span class="run-id">run: {runId.slice(0, 8)}</span>{/if}
		</div>

		{#each drafts as draft}
			<div class="draft-card">
				<div class="draft-header">
					<span class="platform">{draft.platform}</span>
					<span class="draft-meta">
						{#if draft.adherence_warning}<span class="warn">⚠ adherence</span> · {/if}{draft.prompt_tokens + draft.completion_tokens} tokens · ${draft.cost_usd.toFixed(6)} · {draft.model.split('/').pop()}
					</span>
				</div>
				<pre class="draft-content">{draft.content}</pre>
			</div>
		{/each}
	{/if}
</div>

<style>
	.page { display: flex; flex-direction: column; gap: 1rem; }

	.status {
		font-size: 0.8rem;
		padding: 0.4rem 0.75rem;
		border-radius: 4px;
		background: #2a2a2a;
		width: fit-content;
		color: #a3a3a3;
	}
	.status.ok { color: #4ade80; }
	.status.error { color: #f87171; }

	h1 { font-size: 1.5rem; font-weight: 600; }
	.subtitle { color: #a3a3a3; font-size: 0.9rem; }

	textarea {
		width: 100%;
		padding: 0.75rem;
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 6px;
		color: #e5e5e5;
		font-size: 0.95rem;
		resize: vertical;
		box-sizing: border-box;
	}

	.platforms { display: flex; gap: 1.5rem; }
	label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; cursor: pointer; }

	button {
		padding: 0.6rem 1.25rem;
		background: #3b82f6;
		color: #fff;
		border: none;
		border-radius: 6px;
		font-size: 0.9rem;
		cursor: pointer;
		width: fit-content;
	}
	button:disabled { opacity: 0.5; cursor: not-allowed; }
	button:hover:not(:disabled) { background: #2563eb; }

	.error-box {
		padding: 0.75rem;
		background: #2a1a1a;
		border: 1px solid #7f1d1d;
		border-radius: 6px;
		color: #f87171;
		font-size: 0.875rem;
	}

	.meta-row {
		display: flex;
		gap: 1.25rem;
		font-size: 0.8rem;
		color: #a3a3a3;
		padding: 0.5rem 0;
		border-top: 1px solid #2a2a2a;
	}
	.run-id { font-family: monospace; }

	.image-label {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.85rem;
		color: #a3a3a3;
	}
	.image-label input[type="file"] { font-size: 0.8rem; color: #6b7280; }
	.image-name { color: #60a5fa; font-size: 0.8rem; }

	.draft-card {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		overflow: hidden;
	}

	.draft-header {
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

	.draft-meta {
		font-size: 0.75rem;
		color: #6b7280;
	}
	.warn { color: #fbbf24; }

	.draft-content {
		padding: 1rem;
		margin: 0;
		white-space: pre-wrap;
		font-family: inherit;
		font-size: 0.9rem;
		line-height: 1.6;
		color: #e5e5e5;
	}
</style>
