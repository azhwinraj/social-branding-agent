<script lang="ts">
	import { listDrafts, type SavedDraft } from "$lib/api.js";
	import { onMount } from "svelte";
	import { cn, snakeCaseToTitleCase } from "$lib/utils.js";
	import PlatformBadge from "$lib/components/PlatformBadge.svelte";
	import TypeBadge from "$lib/components/TypeBadge.svelte";
	import { Skeleton } from "$lib/components/ui/skeleton/index.js";
	import {
		DropdownMenu,
		DropdownMenuTrigger,
		DropdownMenuContent,
		DropdownMenuItem,
		DropdownMenuSeparator,
		DropdownMenuLabel,
	} from "$lib/components/ui/dropdown-menu/index.js";
	import BookOpen from "@lucide/svelte/icons/book-open";
	import ArrowRight from "@lucide/svelte/icons/arrow-right";
	import ChevronDown from "@lucide/svelte/icons/chevron-down";
	import Check from "@lucide/svelte/icons/check";
	import LayoutGrid from "@lucide/svelte/icons/layout-grid";
	import AlignJustify from "@lucide/svelte/icons/align-justify";
	import ArrowUpDown from "@lucide/svelte/icons/arrow-up-down";
	import TriangleAlert from "@lucide/svelte/icons/triangle-alert";

	// ── State ─────────────────────────────────────────────────────────
	let allDrafts = $state<SavedDraft[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Filter / view state
	let filterPlatform = $state("all");
	let filterType = $state("all");
	let sort = $state<"newest" | "oldest">("newest");
	let view = $state<"list" | "grid">("list");

	onMount(async () => {
		try {
			const all = await listDrafts();
			// History = everything that's been approved or scheduled (not raw pending)
			allDrafts = all.filter((d) => d.status === "approved" || d.status === "scheduled");
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	// ── Derived ───────────────────────────────────────────────────────
	const availableTypes = $derived([
		...new Set(allDrafts.map((d) => d.post_type).filter((t): t is string => !!t)),
	]);

	const filtered = $derived(
		allDrafts
			.filter((d) => filterPlatform === "all" || d.platform === filterPlatform)
			.filter((d) => filterType === "all" || d.post_type === filterType)
			.sort((a, b) => {
				const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
				return sort === "newest" ? -diff : diff;
			})
	);

	// ── Helpers ───────────────────────────────────────────────────────
	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString(undefined, {
			month: "short",
			day: "numeric",
			year: "2-digit",
		});
	}

	const platformLabel = $derived(
		filterPlatform === "all" ? "All platforms" : filterPlatform.charAt(0).toUpperCase() + filterPlatform.slice(1)
	);
	const typeLabel = $derived(
		filterType === "all" ? "All types" : snakeCaseToTitleCase(filterType)
	);
</script>

<div class="space-y-6">
	<!-- ── Heading ──────────────────────────────────────────────────── -->
	<div>
		<h1 class="text-3xl font-semibold text-foreground">History</h1>
		<p class="mt-1 text-sm text-[var(--foreground-muted)]">
			Approved drafts. Style memory uses these automatically when generating new posts.
		</p>
	</div>

	<!-- ══════════════════════════════════════════════════════════════
	     LOADING
	     ══════════════════════════════════════════════════════════════ -->
	{#if loading}
		<div class="space-y-2">
			{#each [1, 2, 3, 4] as _}
				<div class="flex items-center gap-4 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] px-5 py-3.5">
					<Skeleton class="h-5 w-16 rounded" />
					<Skeleton class="h-5 w-24 rounded-md" />
					<Skeleton class="h-5 w-28 rounded-md" />
					<Skeleton class="h-4 flex-1 rounded" />
					<Skeleton class="h-6 w-12 rounded-lg" />
				</div>
			{/each}
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     ERROR
	     ══════════════════════════════════════════════════════════════ -->
	{:else if error}
		<div class="flex items-start gap-2.5 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]">
			<TriangleAlert class="mt-0.5 size-4 shrink-0" />
			{error}
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     EMPTY (no history at all)
	     ══════════════════════════════════════════════════════════════ -->
	{:else if allDrafts.length === 0}
		<div class="flex flex-col items-center gap-4 py-20 text-center">
			<BookOpen class="size-12 text-[var(--foreground-subtle)]" />
			<div>
				<p class="text-lg font-medium text-foreground">No history yet</p>
				<p class="mt-1 max-w-sm text-sm text-[var(--foreground-muted)]">
					Approved drafts appear here for reference. Voice memory uses them automatically when generating new posts.
				</p>
			</div>
			<a
				href="/"
				class="inline-flex items-center gap-1.5 text-sm font-medium text-primary transition-opacity hover:opacity-80"
			>
				Compose your first post <ArrowRight class="size-4" />
			</a>
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     FILTER BAR + RESULTS
	     ══════════════════════════════════════════════════════════════ -->
	{:else}
		<!-- Filter bar -->
		<div class="flex items-center gap-2 flex-wrap">
			<!-- Platform filter -->
			<DropdownMenu>
				<DropdownMenuTrigger
					class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 text-xs font-medium text-[var(--foreground-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-foreground"
				>
					{platformLabel}
					<ChevronDown class="size-3 opacity-60" />
				</DropdownMenuTrigger>
				<DropdownMenuContent class="w-40">
					<DropdownMenuItem onclick={() => (filterPlatform = "all")} class="flex items-center justify-between text-xs">
						All platforms {#if filterPlatform === "all"}<Check class="size-3.5 text-primary" />{/if}
					</DropdownMenuItem>
					<DropdownMenuSeparator />
					{#each ["linkedin", "x", "medium"] as p}
						<DropdownMenuItem onclick={() => (filterPlatform = p)} class="flex items-center justify-between text-xs capitalize">
							{p === "x" ? "X" : p.charAt(0).toUpperCase() + p.slice(1)}
							{#if filterPlatform === p}<Check class="size-3.5 text-primary" />{/if}
						</DropdownMenuItem>
					{/each}
				</DropdownMenuContent>
			</DropdownMenu>

			<!-- Type filter -->
			<DropdownMenu>
				<DropdownMenuTrigger
					class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 text-xs font-medium text-[var(--foreground-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-foreground"
				>
					{typeLabel}
					<ChevronDown class="size-3 opacity-60" />
				</DropdownMenuTrigger>
				<DropdownMenuContent class="w-48">
					<DropdownMenuItem onclick={() => (filterType = "all")} class="flex items-center justify-between text-xs">
						All types {#if filterType === "all"}<Check class="size-3.5 text-primary" />{/if}
					</DropdownMenuItem>
					{#if availableTypes.length > 0}
						<DropdownMenuSeparator />
						{#each availableTypes as t}
							<DropdownMenuItem onclick={() => (filterType = t)} class="flex items-center justify-between text-xs">
								{snakeCaseToTitleCase(t)}
								{#if filterType === t}<Check class="size-3.5 text-primary" />{/if}
							</DropdownMenuItem>
						{/each}
					{/if}
				</DropdownMenuContent>
			</DropdownMenu>

			<!-- Sort -->
			<DropdownMenu>
				<DropdownMenuTrigger
					class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 text-xs font-medium text-[var(--foreground-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-foreground"
				>
					<ArrowUpDown class="size-3 opacity-60" />
					{sort === "newest" ? "Newest first" : "Oldest first"}
				</DropdownMenuTrigger>
				<DropdownMenuContent class="w-36">
					<DropdownMenuItem onclick={() => (sort = "newest")} class="flex items-center justify-between text-xs">
						Newest first {#if sort === "newest"}<Check class="size-3.5 text-primary" />{/if}
					</DropdownMenuItem>
					<DropdownMenuItem onclick={() => (sort = "oldest")} class="flex items-center justify-between text-xs">
						Oldest first {#if sort === "oldest"}<Check class="size-3.5 text-primary" />{/if}
					</DropdownMenuItem>
				</DropdownMenuContent>
			</DropdownMenu>

			<!-- Spacer + view toggle -->
			<div class="ml-auto flex items-center gap-1 rounded-lg border border-[var(--border)] p-0.5">
				<button
					onclick={() => (view = "list")}
					class={cn(
						"flex size-7 items-center justify-center rounded-md transition-colors",
						view === "list"
							? "bg-[var(--background-overlay)] text-foreground"
							: "text-[var(--foreground-subtle)] hover:text-foreground"
					)}
					title="List view"
				>
					<AlignJustify class="size-3.5" />
				</button>
				<button
					onclick={() => (view = "grid")}
					class={cn(
						"flex size-7 items-center justify-center rounded-md transition-colors",
						view === "grid"
							? "bg-[var(--background-overlay)] text-foreground"
							: "text-[var(--foreground-subtle)] hover:text-foreground"
					)}
					title="Grid view"
				>
					<LayoutGrid class="size-3.5" />
				</button>
			</div>
		</div>

		<!-- No filter results -->
		{#if filtered.length === 0}
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] py-12 text-center">
				<p class="text-sm text-[var(--foreground-muted)]">No drafts match the current filters.</p>
				<button
					onclick={() => { filterPlatform = "all"; filterType = "all"; }}
					class="mt-2 text-xs text-primary hover:opacity-80 transition-opacity"
				>
					Clear filters
				</button>
			</div>

		<!-- ── LIST VIEW ──────────────────────────────────────────── -->
		{:else if view === "list"}
			<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] overflow-hidden">
				<!-- Header row -->
				<div class="grid grid-cols-[7rem_1fr_7rem] gap-4 border-b border-[var(--border)] px-5 py-2.5">
					<span class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">Date</span>
					<span class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">Preview</span>
					<span class="text-[10px] font-semibold uppercase tracking-widest text-[var(--foreground-subtle)] text-right">Platform</span>
				</div>

				{#each filtered as draft (draft.id)}
					<div class="group grid grid-cols-[7rem_1fr_7rem] items-center gap-4 border-b border-[var(--border)] px-5 py-3.5 last:border-b-0 hover:bg-[var(--background-overlay)] transition-colors">
						<!-- Date -->
						<span class="text-xs text-[var(--foreground-subtle)] numeric">
							{formatDate(draft.created_at)}
						</span>

						<!-- Preview -->
						<div class="min-w-0">
							<div class="mb-0.5 flex items-center gap-1.5">
								{#if draft.post_type}
									<span class="text-[10px] text-[var(--foreground-subtle)]">{snakeCaseToTitleCase(draft.post_type)}</span>
								{/if}
								{#if draft.status === "scheduled"}
									<span class="text-[10px] text-[var(--warning)]">· scheduled</span>
								{/if}
							</div>
							<p class="truncate text-sm text-foreground">
								{draft.content.slice(0, 120)}{draft.content.length > 120 ? "…" : ""}
							</p>
						</div>

						<!-- Platform -->
						<div class="flex justify-end">
							<PlatformBadge platform={draft.platform as "linkedin" | "x" | "medium"} />
						</div>
					</div>
				{/each}
			</div>

		<!-- ── GRID VIEW ──────────────────────────────────────────── -->
		{:else}
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each filtered as draft (draft.id)}
					<div class="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] overflow-hidden hover:border-[var(--border-strong)] transition-colors">
						<!-- Card header -->
						<div class="flex items-center gap-2 border-b border-[var(--border)] px-4 py-2.5">
							<PlatformBadge platform={draft.platform as "linkedin" | "x" | "medium"} />
							{#if draft.post_type}
								<TypeBadge type={draft.post_type} />
							{/if}
							{#if draft.status === "scheduled"}
								<span class="ml-auto text-[10px] text-[var(--warning)]">scheduled</span>
							{/if}
						</div>

						<!-- Content preview -->
						<p class="flex-1 px-4 py-3.5 text-xs leading-5 text-[var(--foreground-muted)] line-clamp-4">
							{draft.content}
						</p>

						<!-- Footer date -->
						<div class="border-t border-[var(--border)] px-4 py-2">
							<span class="text-[10px] text-[var(--foreground-subtle)] numeric">{formatDate(draft.created_at)}</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Result count -->
		<p class="text-xs text-[var(--foreground-subtle)]">
			{filtered.length} of {allDrafts.length} draft{allDrafts.length !== 1 ? "s" : ""}
		</p>
	{/if}
</div>
