<script lang="ts">
	import {
		listDrafts,
		listRevisions,
		refineInstruction,
		revertRevision,
		regenerateDraft,
		type SavedDraft,
		type Revision,
	} from "$lib/api.js";
	import { onMount } from "svelte";
	import { cn, snakeCaseToTitleCase } from "$lib/utils.js";
	import PlatformBadge from "$lib/components/PlatformBadge.svelte";
	import SchedulePopover from "$lib/components/SchedulePopover.svelte";
	import { Skeleton } from "$lib/components/ui/skeleton/index.js";
	import {
		DropdownMenu,
		DropdownMenuTrigger,
		DropdownMenuContent,
		DropdownMenuItem,
	} from "$lib/components/ui/dropdown-menu/index.js";
	import {
		Tooltip,
		TooltipTrigger,
		TooltipContent,
		TooltipProvider,
	} from "$lib/components/ui/tooltip/index.js";
	import Layers from "@lucide/svelte/icons/layers";
	import ArrowRight from "@lucide/svelte/icons/arrow-right";
	import ChevronDown from "@lucide/svelte/icons/chevron-down";
	import ChevronRight from "@lucide/svelte/icons/chevron-right";
	import Check from "@lucide/svelte/icons/check";
	import Info from "@lucide/svelte/icons/info";
	import Send from "@lucide/svelte/icons/send";
	import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
	import Clock from "@lucide/svelte/icons/clock";

	// ── Constants ────────────────────────────────────────────────────
	const BASE = "http://localhost:8000/api";
	const MAX_REFINEMENTS = 3;

	const PLATFORM_TYPES: Record<string, string[]> = {
		linkedin: ["project_showcase", "technical_deep_dive", "learning", "event_recap", "hot_take", "milestone"],
		x: ["thread", "single_shot", "hot_take", "link_share", "live_event"],
		medium: ["tutorial", "case_study", "opinion", "deep_analysis"],
	};

	// ── Core state ────────────────────────────────────────────────────
	let drafts = $state<SavedDraft[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Per-draft UI state ────────────────────────────────────────────
	let approving     = $state<Record<number, boolean>>({});
	let regenerating  = $state<Record<number, boolean>>({});
	let refining      = $state<Record<number, boolean>>({});
	let reverting     = $state<Record<number, boolean>>({});
	let refineInput   = $state<Record<number, string>>({});
	let contextExpanded = $state<Record<number, boolean>>({});

	// ── Revision history ──────────────────────────────────────────────
	let revisions   = $state<Record<number, Revision[]>>({});
	let softLimitHit = $state<Record<number, boolean>>({});

	// ── Lifecycle ─────────────────────────────────────────────────────
	onMount(async () => {
		try {
			drafts = await listDrafts();
			await Promise.all(
				drafts.map(async (d) => {
					try {
						const data = await listRevisions(d.id);
						revisions = { ...revisions, [d.id]: data.revisions };
					} catch { /* non-fatal */ }
				})
			);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	// ── Helpers ───────────────────────────────────────────────────────
	function parseReasoning(raw: string | null): string {
		if (!raw) return "";
		try {
			return JSON.parse(raw).__reasoning__ ?? "";
		} catch {
			return "";
		}
	}

	function currentRevNum(draftId: number): number {
		return revisions[draftId]?.find((r) => r.is_current)?.revision_number ?? 0;
	}

	function formatScheduledAt(iso: string): string {
		return new Date(iso).toLocaleString(undefined, {
			month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
		});
	}

	// ── Actions ───────────────────────────────────────────────────────
	async function approve(id: number) {
		approving = { ...approving, [id]: true };
		try {
			const res = await fetch(`${BASE}/drafts/${id}/approve`, { method: "POST" });
			if (!res.ok) throw new Error("Approve failed");
			drafts = drafts.map((d) => (d.id === id ? { ...d, status: "approved" } : d));
		} catch (e) {
			alert((e as Error).message);
		} finally {
			approving = { ...approving, [id]: false };
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
			drafts = drafts.map((d) =>
				d.id === draft.id ? { ...d, content: result.revision.content } : d
			);
			const prev = (revisions[draft.id] ?? []).map((r) => ({ ...r, is_current: false }));
			revisions = { ...revisions, [draft.id]: [...prev, result.revision] };
			if (result.warning === "soft_limit_reached") {
				softLimitHit = { ...softLimitHit, [draft.id]: true };
			}
			refineInput = { ...refineInput, [draft.id]: "" };
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
			drafts = drafts.map((d) =>
				d.id === draftId ? { ...d, content: result.current_revision.content } : d
			);
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

	function onScheduled(draftId: number, dt: Date) {
		drafts = drafts.map((d) =>
			d.id === draftId ? { ...d, status: "scheduled", scheduled_at: dt.toISOString() } : d
		);
	}

	// ── Status pill config ────────────────────────────────────────────
	const statusConfig: Record<string, { dot: string; pill: string; label: string }> = {
		approved: { dot: "bg-[var(--success)]", pill: "bg-[var(--success-soft)] text-[var(--success)]", label: "approved" },
		scheduled: { dot: "bg-[var(--warning)] animate-pulse", pill: "bg-[var(--warning-soft)] text-[var(--warning)]", label: "scheduled" },
		pending: { dot: "bg-[var(--foreground-subtle)]", pill: "border border-[var(--border)] text-[var(--foreground-muted)]", label: "pending" },
	};
</script>

<TooltipProvider>
<div class="space-y-4">

	<!-- ── Page heading ───────────────────────────────────────────── -->
	<div>
		<h1 class="text-3xl font-semibold text-foreground">Drafts</h1>
		<p class="mt-1 text-sm text-[var(--foreground-muted)]">Review, refine, approve, and schedule your generated posts.</p>
	</div>

	<!-- ══════════════════════════════════════════════════════════════
	     LOADING
	     ══════════════════════════════════════════════════════════════ -->
	{#if loading}
		{#each [1, 2, 3] as _}
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] overflow-hidden">
				<div class="flex items-center justify-between border-b border-[var(--border)] px-5 py-3">
					<div class="flex items-center gap-2">
						<Skeleton class="h-6 w-24 rounded-md" />
						<Skeleton class="h-5 w-28 rounded-md" />
					</div>
					<Skeleton class="h-5 w-20 rounded-md" />
				</div>
				<div class="space-y-2.5 px-5 py-5">
					<Skeleton class="h-4 w-full rounded" />
					<Skeleton class="h-4 w-full rounded" />
					<Skeleton class="h-4 w-4/5 rounded" />
					<Skeleton class="h-4 w-3/4 rounded" />
				</div>
				<div class="flex items-center gap-3 border-t border-[var(--border)] px-5 py-3">
					<Skeleton class="h-8 w-32 rounded-lg" />
					<Skeleton class="h-8 w-20 rounded-lg" />
				</div>
			</div>
		{/each}

	<!-- ══════════════════════════════════════════════════════════════
	     ERROR
	     ══════════════════════════════════════════════════════════════ -->
	{:else if error}
		<div class="flex items-start gap-2.5 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]">
			<TriangleAlert class="mt-0.5 size-4 shrink-0" />
			{error}
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     EMPTY
	     ══════════════════════════════════════════════════════════════ -->
	{:else if drafts.length === 0}
		<div class="flex flex-col items-center gap-4 py-20 text-center">
			<Layers class="size-12 text-[var(--foreground-subtle)]" />
			<div>
				<p class="text-lg font-medium text-foreground">No drafts yet</p>
				<p class="mt-1 max-w-sm text-sm text-[var(--foreground-muted)]">
					Paste some context on the Compose page to generate your first set of drafts.
				</p>
			</div>
			<a
				href="/"
				class="inline-flex items-center gap-1.5 text-sm font-medium text-primary transition-opacity hover:opacity-80"
			>
				Go to Compose <ArrowRight class="size-4" />
			</a>
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     DRAFT CARDS
	     ══════════════════════════════════════════════════════════════ -->
	{:else}
		{#each drafts as draft (draft.id)}
			{@const types = PLATFORM_TYPES[draft.platform] ?? []}
			{@const draftRevisions = revisions[draft.id] ?? []}
			{@const revNum = currentRevNum(draft.id)}
			{@const reasoning = parseReasoning(draft.post_types_json)}
			{@const sc = statusConfig[draft.status] ?? statusConfig.pending}
			{@const isBusy = regenerating[draft.id] || refining[draft.id] || approving[draft.id]}

			<div
				class={cn(
					"rounded-xl border bg-[var(--background-elevated)] overflow-hidden transition-colors",
					draft.status === "approved" && "border-[var(--success)]/40",
					draft.status === "scheduled" && "border-[var(--warning)]/40",
					draft.status === "pending" && "border-[var(--border)]"
				)}
			>
				<!-- ── Card header ─────────────────────────────────────── -->
				<div class="flex items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-3">
					<!-- Left: platform + type dropdown + reasoning -->
					<div class="flex min-w-0 items-center gap-2">
						<PlatformBadge platform={draft.platform as "linkedin" | "x" | "medium"} />

						{#if types.length > 0}
							<DropdownMenu>
								<DropdownMenuTrigger
									disabled={isBusy}
									class="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--background-overlay)] px-2 py-0.5 text-xs font-medium text-[var(--foreground-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
								>
									{snakeCaseToTitleCase(draft.post_type ?? types[0])}
									{#if regenerating[draft.id]}
										<span class="size-3 animate-spin rounded-full border border-current border-t-transparent"></span>
									{:else}
										<ChevronDown class="size-3 opacity-60" />
									{/if}
								</DropdownMenuTrigger>
								<DropdownMenuContent class="w-48">
									{#each types as t}
										<DropdownMenuItem
											onclick={() => changeType(draft, t)}
											class="flex items-center justify-between text-xs"
										>
											{snakeCaseToTitleCase(t)}
											{#if t === (draft.post_type ?? types[0])}
												<Check class="size-3.5 text-primary" />
											{/if}
										</DropdownMenuItem>
									{/each}
								</DropdownMenuContent>
							</DropdownMenu>

							{#if reasoning}
								<Tooltip>
									<TooltipTrigger class="flex items-center">
										<Info class="size-3.5 text-[var(--foreground-subtle)] hover:text-[var(--foreground-muted)] transition-colors" />
									</TooltipTrigger>
									<TooltipContent class="max-w-xs text-xs">{reasoning}</TooltipContent>
								</Tooltip>
							{/if}
						{/if}
					</div>

					<!-- Right: cost + status pill -->
					<div class="flex shrink-0 items-center gap-2.5">
						<span class="font-mono text-xs numeric text-[var(--foreground-subtle)]">
							${draft.total_cost_usd.toFixed(6)}
						</span>
						<span class={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium", sc.pill)}>
							<span class={cn("size-1.5 rounded-full", sc.dot)}></span>
							{sc.label}
						</span>
					</div>
				</div>

				<!-- ── Draft content ───────────────────────────────────── -->
				<div class={cn("relative px-5 py-5 text-sm leading-7 text-foreground whitespace-pre-wrap", regenerating[draft.id] && "opacity-40 pointer-events-none")}>
					{#if regenerating[draft.id]}
						<div class="absolute inset-0 flex items-center justify-center">
							<p class="animate-pulse text-xs text-[var(--foreground-muted)]">Regenerating…</p>
						</div>
					{/if}
					{draft.content}
				</div>

				<!-- ── Context disclosure ──────────────────────────────── -->
				<div class="mx-5 mb-4">
					<div class="rounded-lg border-l-2 border-[var(--border-strong)] pl-3">
						<button
							onclick={() => (contextExpanded = { ...contextExpanded, [draft.id]: !contextExpanded[draft.id] })}
							class="flex items-center gap-1 text-xs text-[var(--foreground-subtle)] transition-colors hover:text-[var(--foreground-muted)]"
						>
							{#if contextExpanded[draft.id]}
								<ChevronDown class="size-3" />
								<span class="font-medium">Context</span>
							{:else}
								<ChevronRight class="size-3" />
								<span class="font-medium">Context:</span>
								<span class="truncate max-w-xs">{draft.context_input.slice(0, 60)}{draft.context_input.length > 60 ? "…" : ""}</span>
							{/if}
						</button>
						{#if contextExpanded[draft.id]}
							<p class="mt-1.5 text-xs leading-5 text-[var(--foreground-muted)]">{draft.context_input}</p>
						{/if}
					</div>
				</div>

				<!-- ── Refinement panel ────────────────────────────────── -->
				<div class="space-y-3 border-t border-[var(--border)] bg-[var(--background)] px-5 py-4">

					<!-- History strip -->
					{#if draftRevisions.length > 1}
						<div class="flex flex-wrap items-center gap-1.5">
							<span class="text-xs text-[var(--foreground-subtle)]">History</span>
							{#each draftRevisions as rev}
								<button
									title={rev.refinement_instruction ?? undefined}
									disabled={rev.is_current || reverting[draft.id]}
									onclick={() => revert(draft.id, rev.revision_number)}
									class={cn(
										"rounded-md border px-2 py-0.5 font-mono text-xs transition-colors",
										rev.is_current
											? "border-primary bg-[var(--primary-soft)] text-primary"
											: "border-[var(--border)] text-[var(--foreground-muted)] hover:border-[var(--border-strong)] hover:text-foreground disabled:cursor-not-allowed"
									)}
								>
									v{rev.revision_number}{rev.is_current ? " ←" : ""}
								</button>
							{/each}
						</div>
					{/if}

					<!-- Soft-limit warning -->
					{#if softLimitHit[draft.id]}
						<div class="flex items-start gap-2 rounded-lg bg-[var(--warning-soft)] px-3 py-2 text-xs text-[var(--warning)]">
							<TriangleAlert class="mt-0.5 size-3.5 shrink-0" />
							You've reached {MAX_REFINEMENTS} refinements. Drafts can drift after this point.
							<a href="/" class="ml-1 underline underline-offset-2">Start fresh →</a>
						</div>
					{/if}

					<!-- Refine input -->
					<div class="flex gap-2">
						<input
							type="text"
							placeholder='e.g. "Make paragraph 3 less salesy"'
							value={refineInput[draft.id] ?? ""}
							disabled={isBusy}
							oninput={(e) => { refineInput = { ...refineInput, [draft.id]: (e.target as HTMLInputElement).value }; }}
							onkeydown={(e) => { if (e.key === "Enter") sendRefinement(draft); }}
							class="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] px-3 py-1.5 text-sm text-foreground placeholder:text-[var(--foreground-subtle)] outline-none transition-shadow focus:shadow-[0_0_0_2px_var(--primary-soft)] focus:border-[var(--border-strong)] disabled:opacity-50"
						/>
						<button
							onclick={() => sendRefinement(draft)}
							disabled={isBusy || !refineInput[draft.id]?.trim()}
							class="inline-flex h-8 w-16 items-center justify-center gap-1.5 rounded-lg bg-[var(--background-overlay)] text-xs font-medium text-[var(--foreground-muted)] transition-colors hover:bg-[var(--border)] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
						>
							{#if refining[draft.id]}
								<span class="size-3.5 animate-spin rounded-full border border-current border-t-transparent"></span>
							{:else}
								<Send class="size-3.5" />
								Send
							{/if}
						</button>
					</div>

					<p class="text-xs text-[var(--foreground-subtle)]">
						Tip: be specific — "Make paragraph 3 less salesy" works better than "make it better"
					</p>
				</div>

				<!-- ── Action footer ───────────────────────────────────── -->
				<div class="flex items-center gap-2 border-t border-[var(--border)] px-5 py-3">
					{#if draft.status === "scheduled" && draft.scheduled_at}
						<span class="flex items-center gap-1.5 text-xs text-[var(--warning)]">
							<Clock class="size-3.5" />
							Scheduled for {formatScheduledAt(draft.scheduled_at)}
						</span>
					{:else}
						<!-- Approve -->
						{#if draft.status !== "approved"}
							<button
								onclick={() => approve(draft.id)}
								disabled={isBusy}
								class="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
							>
								{#if approving[draft.id]}
									<span class="size-3.5 animate-spin rounded-full border border-white/20 border-t-white"></span>
									Approving…
								{:else}
									<Check class="size-3.5" />
									Approve &amp; save voice
								{/if}
							</button>
						{:else}
							<span class="flex items-center gap-1.5 text-xs text-[var(--success)]">
								<Check class="size-3.5" />
								Approved
							</span>
						{/if}

						<!-- Schedule popover -->
						<SchedulePopover
							draftId={draft.id}
							disabled={isBusy}
							onScheduled={(dt) => onScheduled(draft.id, dt)}
						/>

						<!-- Discard (no API yet — placeholder) -->
						<button
							disabled
							title="Coming in a future update"
							class="ml-auto inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-medium text-[var(--danger)] opacity-40 cursor-not-allowed"
						>
							Discard
						</button>
					{/if}
				</div>
			</div>
		{/each}
	{/if}

</div>
</TooltipProvider>
