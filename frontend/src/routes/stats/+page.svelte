<script lang="ts">
	import { getStats, type Stats } from '$lib/api';
	import { onMount } from 'svelte';

	let stats = $state<Stats | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			stats = await getStats();
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	function fmt(n: number) {
		return n.toLocaleString();
	}

	function fmtCost(n: number) {
		return `$${n.toFixed(6)}`;
	}

	function shortModel(m: string) {
		return m.split('/').pop() ?? m;
	}

	function totalDrafts(d: Record<string, number>) {
		return Object.values(d).reduce((a, b) => a + b, 0);
	}
</script>

<div class="page">
	<h1>Stats</h1>
	<p class="subtitle">LLM cost and token telemetry — matches your provider billing dashboards.</p>

	{#if loading}
		<p class="muted">Loading...</p>
	{:else if error}
		<p class="err">{error}</p>
	{:else if stats}
		<!-- Summary cards -->
		<div class="cards">
			<div class="card">
				<span class="card-label">Total LLM Calls</span>
				<span class="card-value">{fmt(stats.totals.calls)}</span>
			</div>
			<div class="card">
				<span class="card-label">Total Tokens</span>
				<span class="card-value">{fmt(stats.totals.total_tokens)}</span>
				<span class="card-sub">{fmt(stats.totals.prompt_tokens)} prompt · {fmt(stats.totals.completion_tokens)} completion</span>
			</div>
			<div class="card">
				<span class="card-label">Total Cost</span>
				<span class="card-value">{fmtCost(stats.totals.cost_usd)}</span>
			</div>
			<div class="card">
				<span class="card-label">Drafts Generated</span>
				<span class="card-value">{fmt(totalDrafts(stats.drafts))}</span>
				<span class="card-sub">
					{stats.drafts['approved'] ?? 0} approved ·
					{stats.drafts['scheduled'] ?? 0} scheduled
				</span>
			</div>
		</div>

		<!-- By model -->
		{#if stats.by_model.length > 0}
			<section>
				<h2>By Model</h2>
				<table>
					<thead>
						<tr>
							<th>Model</th>
							<th class="num">Calls</th>
							<th class="num">Tokens</th>
							<th class="num">Cost</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.by_model as row}
							<tr>
								<td class="mono">{shortModel(row.model)}</td>
								<td class="num">{fmt(row.calls)}</td>
								<td class="num">{fmt(row.tokens)}</td>
								<td class="num">{fmtCost(row.cost_usd)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		{/if}

		<!-- By node -->
		{#if stats.by_node.length > 0}
			<section>
				<h2>By Node</h2>
				<table>
					<thead>
						<tr>
							<th>Node</th>
							<th class="num">Calls</th>
							<th class="num">Tokens</th>
							<th class="num">Cost</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.by_node as row}
							<tr>
								<td class="mono">{row.node}</td>
								<td class="num">{fmt(row.calls)}</td>
								<td class="num">{fmt(row.tokens)}</td>
								<td class="num">{fmtCost(row.cost_usd)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		{/if}

		<!-- By day -->
		{#if stats.by_day.length > 0}
			<section>
				<h2>By Day</h2>
				<table>
					<thead>
						<tr>
							<th>Date</th>
							<th class="num">Calls</th>
							<th class="num">Tokens</th>
							<th class="num">Cost</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.by_day as row}
							<tr>
								<td>{row.date}</td>
								<td class="num">{fmt(row.calls)}</td>
								<td class="num">{fmt(row.tokens)}</td>
								<td class="num">{fmtCost(row.cost_usd)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		{/if}

		{#if stats.totals.calls === 0}
			<p class="muted">No LLM calls recorded yet. Generate some drafts to see telemetry here.</p>
		{/if}
	{/if}
</div>

<style>
	.page { display: flex; flex-direction: column; gap: 1.5rem; }
	h1 { font-size: 1.5rem; font-weight: 600; }
	h2 { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; color: #d1d5db; }
	.subtitle { color: #a3a3a3; font-size: 0.9rem; margin-top: -1rem; }
	.muted { color: #6b7280; font-size: 0.9rem; }
	.err { color: #f87171; font-size: 0.9rem; }

	.cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 0.75rem;
	}

	.card {
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.card-label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
	.card-value { font-size: 1.5rem; font-weight: 700; color: #e5e5e5; }
	.card-sub { font-size: 0.72rem; color: #4b5563; }

	section { display: flex; flex-direction: column; }

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	th {
		text-align: left;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		border-bottom: 1px solid #2a2a2a;
	}

	td {
		padding: 0.5rem 0.75rem;
		color: #d1d5db;
		border-bottom: 1px solid #1f1f1f;
	}

	tr:last-child td { border-bottom: none; }
	tr:hover td { background: #1f1f1f; }

	.num { text-align: right; font-variant-numeric: tabular-nums; }
	.mono { font-family: monospace; font-size: 0.8rem; color: #93c5fd; }
</style>
