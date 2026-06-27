<script lang="ts">
	import { getStats, type Stats } from "$lib/api.js";
	import { onMount } from "svelte";
	import { Skeleton } from "$lib/components/ui/skeleton/index.js";
	import BarChart2 from "@lucide/svelte/icons/bar-chart-2";
	import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
	import TrendingUp from "@lucide/svelte/icons/trending-up";

	// ── State ──────────────────────────────────────────────────────────
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

	// ── Helpers ────────────────────────────────────────────────────────
	function fmt(n: number): string {
		return n.toLocaleString();
	}

	function shortModel(m: string): string {
		return m.split("/").pop() ?? m;
	}

	function totalDrafts(d: Record<string, number>): number {
		return Object.values(d).reduce((a, b) => a + b, 0);
	}

	// ── SVG Sparkline ─────────────────────────────────────────────────
	function sparklinePath(values: number[], w = 72, h = 24): string {
		if (values.length < 2) return "";
		const max = Math.max(...values, 0.000001);
		const pts = values.map(
			(v, i) => `${(i / (values.length - 1)) * w},${h - (v / max) * h * 0.85 - 2}`
		);
		return `M ${pts.join(" L ")}`;
	}

	// ── SVG Area chart ────────────────────────────────────────────────
	type DayPoint = { cost_usd: number };
	function areaChartPaths(data: DayPoint[], w: number, h: number) {
		if (data.length < 2) return { line: "", area: "" };
		const max = Math.max(...data.map((d) => d.cost_usd), 0.000001);
		const pts = data.map((d, i) => ({
			x: (i / (data.length - 1)) * w,
			y: h - (d.cost_usd / max) * (h - 8) - 4,
		}));
		const line = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
		const area = `${line} L ${w} ${h} L 0 ${h} Z`;
		return { line, area };
	}

	// ── SVG Donut chart ────────────────────────────────────────────────
	const DONUT_COLORS = [
		"oklch(0.65 0.22 295)",
		"oklch(0.48 0 0)",
		"oklch(0.40 0 0)",
		"oklch(0.33 0 0)",
		"oklch(0.27 0 0)",
	];

	interface DonutSlice {
		label: string;
		pct: number;
		path: string;
		color: string;
	}

	function computeDonut(items: { label: string; tokens: number }[], R = 56, r = 34): DonutSlice[] {
		const total = items.reduce((s, d) => s + d.tokens, 0);
		if (total === 0) return [];
		let angle = -Math.PI / 2;
		return items.map((d, i) => {
			const slice = (d.tokens / total) * 2 * Math.PI;
			const sa = angle;
			const ea = angle + slice;
			angle = ea;
			const x1 = Math.cos(sa) * R, y1 = Math.sin(sa) * R;
			const x2 = Math.cos(ea) * R, y2 = Math.sin(ea) * R;
			const ix1 = Math.cos(sa) * r, iy1 = Math.sin(sa) * r;
			const ix2 = Math.cos(ea) * r, iy2 = Math.sin(ea) * r;
			const la = slice > Math.PI ? 1 : 0;
			const path =
				`M ${x1} ${y1} A ${R} ${R} 0 ${la} 1 ${x2} ${y2}` +
				` L ${ix2} ${iy2} A ${r} ${r} 0 ${la} 0 ${ix1} ${iy1} Z`;
			return {
				label: d.label,
				pct: d.tokens / total,
				path,
				color: DONUT_COLORS[i] ?? DONUT_COLORS[DONUT_COLORS.length - 1],
			};
		});
	}

	// ── Money saved ────────────────────────────────────────────────────
	// Compares against Claude Sonnet 4.6 blended rate (~$6/1M tokens)
	const SONNET_RATE = 6 / 1_000_000;

	const savings = $derived(
		stats
			? (() => {
					const freeRows = stats.by_model.filter((m) => m.cost_usd === 0);
					const freeTokens = freeRows.reduce((s, m) => s + m.tokens, 0);
					const freeCalls = freeRows.reduce((s, m) => s + m.calls, 0);
					return {
						saved: freeTokens * SONNET_RATE,
						pct:
							stats.totals.calls > 0
								? Math.round((freeCalls / stats.totals.calls) * 100)
								: 0,
						freeCalls,
					};
				})()
			: { saved: 0, pct: 0, freeCalls: 0 }
	);

	// ── Chart data ─────────────────────────────────────────────────────
	const dayData = $derived(stats?.by_day.slice(-14) ?? []);

	const modelData = $derived(
		(stats?.by_model ?? [])
			.filter((m) => m.tokens > 0)
			.map((m) => ({ ...m, label: shortModel(m.model) }))
			.sort((a, b) => b.tokens - a.tokens)
			.slice(0, 5)
	);

	const donutSlices = $derived(computeDonut(modelData));

	const nodeData = $derived((stats?.by_node ?? []).sort((a, b) => b.calls - a.calls));
	const maxNodeCalls = $derived(nodeData[0]?.calls ?? 1);

	const sparkCost = $derived(dayData.map((d) => d.cost_usd));
	const sparkCalls = $derived(dayData.map((d) => d.calls));

	const CHART_W = 340;
	const CHART_H = 120;
	const areaPaths = $derived(areaChartPaths(dayData, CHART_W, CHART_H));
</script>

<div class="space-y-6">
	<!-- ── Heading ──────────────────────────────────────────────────── -->
	<div>
		<h1 class="text-3xl font-semibold text-foreground">Stats</h1>
		<p class="mt-1 text-sm text-[var(--foreground-muted)]">
			LLM cost and token telemetry — matches your provider dashboards.
		</p>
	</div>

	<!-- ══════════════════════════════════════════════════════════════
	     LOADING
	     ══════════════════════════════════════════════════════════════ -->
	{#if loading}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each [1, 2, 3, 4] as _}
				<div
					class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-4 space-y-2"
				>
					<Skeleton class="h-3 w-20 rounded" />
					<Skeleton class="h-8 w-16 rounded" />
				</div>
			{/each}
		</div>
		<div class="grid gap-3 lg:grid-cols-3">
			<div
				class="lg:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5"
			>
				<Skeleton class="h-4 w-36 rounded mb-4" />
				<Skeleton class="h-32 w-full rounded-lg" />
			</div>
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5">
				<Skeleton class="h-4 w-28 rounded mb-4" />
				<Skeleton class="h-32 w-full rounded" />
			</div>
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     ERROR
	     ══════════════════════════════════════════════════════════════ -->
	{:else if error}
		<div
			class="flex items-start gap-2.5 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]"
		>
			<TriangleAlert class="mt-0.5 size-4 shrink-0" />
			{error}
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     NO DATA
	     ══════════════════════════════════════════════════════════════ -->
	{:else if !stats || stats.totals.calls === 0}
		<div class="flex flex-col items-center gap-4 py-20 text-center">
			<BarChart2 class="size-12 text-[var(--foreground-subtle)]" />
			<div>
				<p class="text-lg font-medium text-foreground">No telemetry yet</p>
				<p class="mt-1 max-w-sm text-sm text-[var(--foreground-muted)]">
					Generate your first draft to start seeing LLM cost and token data here.
				</p>
			</div>
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     DASHBOARD
	     ══════════════════════════════════════════════════════════════ -->
	{:else if stats}

		<!-- ── Row 1: Stat cards ──────────────────────────────────────── -->
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<!-- Calls -->
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-4">
				<p class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">
					LLM Calls
				</p>
				<p class="mt-1 text-3xl font-semibold numeric text-foreground">{fmt(stats.totals.calls)}</p>
				{#if sparkCalls.length >= 2}
					<svg viewBox="0 0 72 24" class="mt-2 w-full" style="height:24px" preserveAspectRatio="none">
						<path
							d={sparklinePath(sparkCalls)}
							fill="none"
							stroke="oklch(0.65 0.22 295)"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>
				{/if}
			</div>

			<!-- Tokens -->
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-4">
				<p class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">
					Tokens
				</p>
				<p class="mt-1 text-3xl font-semibold numeric text-foreground">
					{fmt(stats.totals.total_tokens)}
				</p>
				<p class="mt-1 text-[10px] numeric text-[var(--foreground-subtle)]">
					{fmt(stats.totals.prompt_tokens)}↑ · {fmt(stats.totals.completion_tokens)}↓
				</p>
			</div>

			<!-- Cost -->
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-4">
				<p class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">
					Cost
				</p>
				<p class="mt-1 text-3xl font-semibold numeric text-foreground">
					${stats.totals.cost_usd.toFixed(6)}
				</p>
				{#if sparkCost.length >= 2}
					<svg viewBox="0 0 72 24" class="mt-2 w-full" style="height:24px" preserveAspectRatio="none">
						<path
							d={sparklinePath(sparkCost)}
							fill="none"
							stroke="oklch(0.65 0.22 295)"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>
				{/if}
			</div>

			<!-- Drafts -->
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-4">
				<p class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">
					Drafts
				</p>
				<p class="mt-1 text-3xl font-semibold numeric text-foreground">
					{fmt(totalDrafts(stats.drafts))}
				</p>
				<p class="mt-1 text-[10px] numeric text-[var(--foreground-subtle)]">
					{stats.drafts["approved"] ?? 0} approved · {stats.drafts["scheduled"] ?? 0} scheduled
				</p>
			</div>
		</div>

		<!-- ── Row 2: Daily cost + Model donut ────────────────────────── -->
		<div class="grid gap-3 lg:grid-cols-3">
			<!-- Daily cost area chart -->
			<div class="lg:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5">
				<p class="mb-4 text-sm font-medium text-foreground">Daily cost — last 14 days</p>
				{#if dayData.length >= 2}
					<svg
						viewBox="0 0 {CHART_W} {CHART_H}"
						class="w-full"
						style="height:120px"
						preserveAspectRatio="none"
					>
						<defs>
							<linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
								<stop offset="0%" stop-color="oklch(0.65 0.22 295)" stop-opacity="0.18" />
								<stop offset="100%" stop-color="oklch(0.65 0.22 295)" stop-opacity="0" />
							</linearGradient>
						</defs>
						<path d={areaPaths.area} fill="url(#area-grad)" />
						<path
							d={areaPaths.line}
							fill="none"
							stroke="oklch(0.65 0.22 295)"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>
					<div class="mt-1 flex justify-between">
						<span class="text-[10px] numeric text-[var(--foreground-subtle)]">{dayData[0]?.date ?? ""}</span>
						<span class="text-[10px] numeric text-[var(--foreground-subtle)]">{dayData[dayData.length - 1]?.date ?? ""}</span>
					</div>
				{:else}
					<div
						class="flex h-32 items-center justify-center rounded-lg border border-dashed border-[var(--border)]"
					>
						<p class="text-xs text-[var(--foreground-subtle)]">Not enough data — generate more drafts</p>
					</div>
				{/if}
			</div>

			<!-- Tokens by model donut -->
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5">
				<p class="mb-4 text-sm font-medium text-foreground">Tokens by model</p>
				{#if donutSlices.length > 0}
					<div class="flex items-center gap-4">
						<svg viewBox="-64 -64 128 128" class="size-28 shrink-0">
							{#each donutSlices as slice}
								<path d={slice.path} fill={slice.color} />
							{/each}
						</svg>
						<div class="min-w-0 space-y-1.5">
							{#each donutSlices as slice}
								<div class="flex items-center gap-1.5 min-w-0 text-xs">
									<span
										class="size-2 shrink-0 rounded-full"
										style="background:{slice.color}"
									></span>
									<span class="truncate font-mono text-[var(--foreground-muted)]">{slice.label}</span>
									<span class="ml-auto shrink-0 numeric text-[var(--foreground-subtle)]">
										{Math.round(slice.pct * 100)}%
									</span>
								</div>
							{/each}
						</div>
					</div>
				{:else}
					<div
						class="flex h-32 items-center justify-center rounded-lg border border-dashed border-[var(--border)]"
					>
						<p class="text-xs text-[var(--foreground-subtle)]">No model data yet</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- ── Row 3: Calls by node + Money saved ─────────────────────── -->
		<div class="grid gap-3 lg:grid-cols-3">
			<!-- Calls by node bar chart -->
			<div class="lg:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5">
				<p class="mb-4 text-sm font-medium text-foreground">Calls by node</p>
				{#if nodeData.length > 0}
					<div class="space-y-3">
						{#each nodeData as node}
							<div class="flex items-center gap-3">
								<span
									class="w-36 shrink-0 truncate text-right font-mono text-xs text-[var(--foreground-muted)]"
								>
									{node.node}
								</span>
								<div
									class="flex-1 overflow-hidden rounded-full bg-[var(--background-overlay)]"
									style="height:6px"
								>
									<div
										class="h-full rounded-full bg-primary transition-all"
										style="width:{Math.max(2, (node.calls / maxNodeCalls) * 100)}%"
									></div>
								</div>
								<span class="w-6 shrink-0 text-right text-xs numeric text-[var(--foreground-subtle)]">
									{node.calls}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-xs text-[var(--foreground-subtle)]">No node data yet.</p>
				{/if}
			</div>

			<!-- Money saved narrative -->
			<div
				class="flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5"
			>
				<div class="flex items-center gap-2">
					<TrendingUp class="size-4 text-[var(--success)]" />
					<p class="text-sm font-medium text-foreground">Money saved</p>
				</div>

				<div>
					<p class="text-3xl font-semibold numeric text-foreground">${savings.saved.toFixed(4)}</p>
					<p class="mt-0.5 text-xs text-[var(--foreground-subtle)]">
						vs. all calls on Claude Sonnet 4.6
					</p>
				</div>

				<div class="rounded-lg bg-[var(--success-soft)] px-3 py-2">
					<p class="text-xs font-medium text-[var(--success)]">{savings.pct}% of calls at $0</p>
					<p class="mt-0.5 text-xs text-[var(--foreground-muted)]">
						{fmt(savings.freeCalls)} of {fmt(stats.totals.calls)} calls on free tier
					</p>
				</div>

				<p class="text-[10px] leading-4 text-[var(--foreground-subtle)]">
					Estimated at $6/1M tokens blended (Sonnet 4.6: $3 input + $15 output).
				</p>
			</div>
		</div>

		<!-- ── Row 4: Model breakdown table ───────────────────────────── -->
		{#if stats.by_model.length > 0}
			<div class="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--background-elevated)]">
				<div class="border-b border-[var(--border)] px-5 py-3">
					<p class="text-sm font-medium text-foreground">Model breakdown</p>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full text-xs">
						<thead>
							<tr class="border-b border-[var(--border)]">
								<th
									class="px-5 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]"
									>Model</th
								>
								<th
									class="px-5 py-2.5 text-right text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]"
									>Calls</th
								>
								<th
									class="px-5 py-2.5 text-right text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]"
									>Tokens</th
								>
								<th
									class="px-5 py-2.5 text-right text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]"
									>Cost</th
								>
							</tr>
						</thead>
						<tbody>
							{#each stats.by_model as row}
								<tr
									class="border-b border-[var(--border)] last:border-b-0 transition-colors hover:bg-[var(--background-overlay)]"
								>
									<td class="px-5 py-3 font-mono text-[var(--foreground-muted)]"
										>{shortModel(row.model)}</td
									>
									<td class="px-5 py-3 text-right numeric text-[var(--foreground-muted)]"
										>{fmt(row.calls)}</td
									>
									<td class="px-5 py-3 text-right numeric text-[var(--foreground-muted)]"
										>{fmt(row.tokens)}</td
									>
									<td class="px-5 py-3 text-right numeric text-[var(--foreground-muted)]"
										>${row.cost_usd.toFixed(6)}</td
									>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

	{/if}
</div>
