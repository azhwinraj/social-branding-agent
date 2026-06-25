<script lang="ts">
	import { healthCheck, generate } from '$lib/api';
	import { onMount } from 'svelte';

	let backendStatus = $state<'checking' | 'ok' | 'error'>('checking');
	let context = $state('');
	let platforms = $state(['linkedin', 'x', 'medium']);
	let loading = $state(false);
	let result = $state<string | null>(null);

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
		result = null;
		try {
			const data = await generate(context, platforms);
			result = `Run ID: ${data.run_id || 'n/a'} — ${data.drafts.length} drafts generated (stubs for now)`;
		} catch (e) {
			result = 'Error: ' + (e as Error).message;
		} finally {
			loading = false;
		}
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

	{#if result}
		<div class="result">{result}</div>
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

	.result {
		padding: 0.75rem;
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 6px;
		font-size: 0.875rem;
		color: #a3a3a3;
	}
</style>
