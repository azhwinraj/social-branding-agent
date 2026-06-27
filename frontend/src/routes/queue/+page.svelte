<script lang="ts">
	import { listDrafts, type SavedDraft } from "$lib/api.js";
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { snakeCaseToTitleCase } from "$lib/utils.js";
	import PlatformBadge from "$lib/components/PlatformBadge.svelte";
	import TypeBadge from "$lib/components/TypeBadge.svelte";
	import { Skeleton } from "$lib/components/ui/skeleton/index.js";
	import CalendarClock from "@lucide/svelte/icons/calendar-clock";
	import Clock from "@lucide/svelte/icons/clock";
	import Bell from "@lucide/svelte/icons/bell";
	import Pencil from "@lucide/svelte/icons/pencil";
	import ArrowRight from "@lucide/svelte/icons/arrow-right";
	import TriangleAlert from "@lucide/svelte/icons/triangle-alert";

	// ── State ────────────────────────────────────────────────────────
	let allDrafts = $state<SavedDraft[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const all = await listDrafts();
			allDrafts = all
				.filter((d) => d.status === "scheduled" && d.scheduled_at)
				.sort((a, b) => new Date(a.scheduled_at!).getTime() - new Date(b.scheduled_at!).getTime());
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	});

	// ── Helpers ───────────────────────────────────────────────────────
	function relativeTime(iso: string): string {
		const diff = new Date(iso).getTime() - Date.now();
		const mins = Math.round(diff / 60000);
		if (mins < 0) return "overdue";
		if (mins < 60) return `in ${mins}m`;
		const hrs = Math.round(mins / 60);
		if (hrs < 24) return `in ${hrs}h`;
		const days = Math.round(hrs / 24);
		return `in ${days}d`;
	}

	function formatTime(iso: string): string {
		return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
	}

	function dayLabel(iso: string): string {
		const d = new Date(iso);
		const today = new Date();
		const tomorrow = new Date(Date.now() + 86_400_000);
		if (d.toDateString() === today.toDateString()) return "Today";
		if (d.toDateString() === tomorrow.toDateString()) return "Tomorrow";
		return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
	}

	function computeGrouped(drafts: SavedDraft[]) {
		const map = new Map<string, SavedDraft[]>();
		for (const d of drafts) {
			if (!d.scheduled_at) continue;
			const key = new Date(d.scheduled_at).toDateString();
			const existing = map.get(key);
			if (existing) existing.push(d);
			else map.set(key, [d]);
		}
		return Array.from(map.entries()).map(([, items]) => ({
			label: dayLabel(items[0].scheduled_at!),
			items,
		}));
	}

	const grouped = $derived(computeGrouped(allDrafts));
</script>

<div class="space-y-6">
	<!-- ── Heading ──────────────────────────────────────────────────── -->
	<div>
		<h1 class="text-3xl font-semibold text-foreground">Queue</h1>
		<p class="mt-1 text-sm text-[var(--foreground-muted)]">
			Scheduled posts, sorted by date. You'll be notified at post time.
		</p>
	</div>

	<!-- ══════════════════════════════════════════════════════════════
	     LOADING
	     ══════════════════════════════════════════════════════════════ -->
	{#if loading}
		<div class="space-y-3">
			{#each [1, 2] as _}
				<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5">
					<div class="mb-3 flex items-center gap-2">
						<Skeleton class="h-6 w-24 rounded-md" />
						<Skeleton class="h-5 w-28 rounded-md" />
					</div>
					<Skeleton class="mb-4 h-4 w-full rounded" />
					<Skeleton class="h-4 w-3/4 rounded" />
					<div class="mt-4 flex items-center justify-between">
						<Skeleton class="h-4 w-28 rounded" />
						<Skeleton class="h-7 w-16 rounded-lg" />
					</div>
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
	     EMPTY
	     ══════════════════════════════════════════════════════════════ -->
	{:else if allDrafts.length === 0}
		<div class="flex flex-col items-center gap-4 py-20 text-center">
			<CalendarClock class="size-12 text-[var(--foreground-subtle)]" />
			<div>
				<p class="text-lg font-medium text-foreground">No scheduled posts</p>
				<p class="mt-1 max-w-sm text-sm text-[var(--foreground-muted)]">
					When you approve a draft and schedule it, it'll appear here sorted by date.
				</p>
			</div>
			<a
				href="/drafts"
				class="inline-flex items-center gap-1.5 text-sm font-medium text-primary transition-opacity hover:opacity-80"
			>
				Go to Drafts <ArrowRight class="size-4" />
			</a>
		</div>

	<!-- ══════════════════════════════════════════════════════════════
	     DAY-GROUPED QUEUE
	     ══════════════════════════════════════════════════════════════ -->
	{:else}
		<div class="space-y-8">
			{#each grouped as group}
				<!-- Day header -->
				<div>
					<p class="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--foreground-subtle)]">
						{group.label}
					</p>

					<div class="space-y-3">
						{#each group.items as draft (draft.id)}
							{@const isOverdue = relativeTime(draft.scheduled_at!) === "overdue"}

							<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5">
								<!-- Platform + type -->
								<div class="mb-3 flex items-center gap-2">
									<PlatformBadge platform={draft.platform as "linkedin" | "x" | "medium"} />
									{#if draft.post_type}
										<TypeBadge type={draft.post_type} />
									{/if}
								</div>

								<!-- Content preview (2-3 lines) -->
								<p class="line-clamp-3 text-sm leading-6 text-foreground">
									{draft.content}
								</p>

								<!-- Time row -->
								<div class="mt-4 flex items-center justify-between gap-4">
									<span
										class="flex items-center gap-1.5 text-xs {isOverdue ? 'text-[var(--danger)]' : 'text-[var(--foreground-muted)]'}"
									>
										<Clock class="size-3.5" />
										{formatTime(draft.scheduled_at!)}
										<span class="text-[var(--foreground-subtle)]">·</span>
										<span class="{isOverdue ? 'text-[var(--danger)] font-medium' : 'text-[var(--foreground-subtle)]'}">
											{relativeTime(draft.scheduled_at!)}
										</span>
									</span>

									<!-- Actions -->
									<div class="flex items-center gap-2">
										<button
											onclick={() => goto("/drafts")}
											class="inline-flex h-7 items-center gap-1 rounded-lg border border-[var(--border)] px-2.5 text-xs text-[var(--foreground-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-foreground"
										>
											<Pencil class="size-3" />
											Edit
										</button>
										<button
											disabled
											title="Cancel scheduling — coming soon"
											class="inline-flex h-7 items-center gap-1 rounded-lg px-2.5 text-xs text-[var(--danger)] opacity-40 cursor-not-allowed"
										>
											Cancel
										</button>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>

		<!-- Notification banner -->
		<div class="flex items-start gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] px-4 py-3">
			<Bell class="mt-0.5 size-4 shrink-0 text-[var(--foreground-subtle)]" />
			<p class="text-xs text-[var(--foreground-muted)]">
				You'll be notified on <span class="text-foreground font-medium">Desktop + Phone</span> at the scheduled time.
				Notification settings can be configured in Settings.
			</p>
		</div>
	{/if}
</div>
