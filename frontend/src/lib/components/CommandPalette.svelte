<script lang="ts">
	import { goto } from "$app/navigation";
	import { toggleMode, mode } from "mode-watcher";
	import { listDrafts, type SavedDraft } from "$lib/api.js";
	import {
		CommandDialog,
		CommandEmpty,
		CommandGroup,
		CommandInput,
		CommandItem,
		CommandList,
		CommandSeparator,
		CommandShortcut,
	} from "$lib/components/ui/command/index.js";
	import LayoutDashboard from "@lucide/svelte/icons/layout-dashboard";
	import FileText from "@lucide/svelte/icons/file-text";
	import CalendarClock from "@lucide/svelte/icons/calendar-clock";
	import BookOpen from "@lucide/svelte/icons/book-open";
	import BarChart2 from "@lucide/svelte/icons/bar-chart-2";
	import Moon from "@lucide/svelte/icons/moon";
	import Sun from "@lucide/svelte/icons/sun";
	import Search from "@lucide/svelte/icons/search";

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	let search = $state("");
	let drafts = $state<SavedDraft[]>([]);
	let draftsLoaded = $state(false);

	// Load drafts lazily on first open
	$effect(() => {
		if (open && !draftsLoaded) {
			listDrafts()
				.then((all) => {
					drafts = all;
					draftsLoaded = true;
				})
				.catch(() => {
					draftsLoaded = true;
				});
		}
	});

	const navItems = [
		{ value: "nav:compose", label: "Compose", href: "/", icon: LayoutDashboard, shortcut: "⌘1" },
		{ value: "nav:drafts", label: "Drafts", href: "/drafts", icon: FileText, shortcut: "⌘2" },
		{ value: "nav:queue", label: "Queue", href: "/queue", icon: CalendarClock, shortcut: "⌘3" },
		{ value: "nav:history", label: "History", href: "/history", icon: BookOpen, shortcut: "⌘4" },
		{ value: "nav:stats", label: "Stats", href: "/stats", icon: BarChart2, shortcut: "⌘5" },
	];

	function navigate(href: string) {
		open = false;
		goto(href);
	}

	function handleToggleMode() {
		open = false;
		toggleMode();
	}

	// Filtered draft results: require ≥2 chars in search
	const draftResults = $derived(
		search.length >= 2
			? drafts
					.filter(
						(d) =>
							d.content.toLowerCase().includes(search.toLowerCase()) ||
							d.platform.toLowerCase().includes(search.toLowerCase())
					)
					.slice(0, 5)
			: []
	);

	// Custom filter: always show nav/action items, filter drafts by search
	function commandFilter(value: string, _search: string): number {
		if (value.startsWith("nav:") || value.startsWith("action:")) return 1;
		return 0; // drafts are shown via {#each} conditionally, not cmdk filtering
	}
</script>

<CommandDialog
	bind:open
	title="Command Palette"
	description="Navigate, search drafts, or run actions"
	filter={commandFilter}
>
	<CommandInput
		bind:value={search}
		placeholder="Search or navigate…"
		class="text-sm"
	/>
	<CommandList class="max-h-80">
		<CommandEmpty>
			{#if !draftsLoaded && search.length >= 2}
				<span class="text-xs text-[var(--foreground-subtle)]">Loading…</span>
			{:else}
				<span class="text-xs text-[var(--foreground-subtle)]">No results for "{search}"</span>
			{/if}
		</CommandEmpty>

		<!-- Navigation -->
		<CommandGroup heading="Navigate">
			{#each navItems as item}
				<CommandItem
					value={item.value}
					onSelect={() => navigate(item.href)}
					class="flex items-center gap-2.5 text-sm"
				>
					<item.icon class="size-4 shrink-0 text-[var(--foreground-subtle)]" />
					{item.label}
					<CommandShortcut>{item.shortcut}</CommandShortcut>
				</CommandItem>
			{/each}
		</CommandGroup>

		<CommandSeparator />

		<!-- Actions -->
		<CommandGroup heading="Actions">
			<CommandItem
				value="action:theme"
				onSelect={handleToggleMode}
				class="flex items-center gap-2.5 text-sm"
			>
				{#if mode.current === "dark"}
					<Sun class="size-4 shrink-0 text-[var(--foreground-subtle)]" />
					Switch to Light mode
				{:else}
					<Moon class="size-4 shrink-0 text-[var(--foreground-subtle)]" />
					Switch to Dark mode
				{/if}
				<CommandShortcut>⌘D</CommandShortcut>
			</CommandItem>
		</CommandGroup>

		<!-- Draft search results (shown when search ≥2 chars) -->
		{#if draftResults.length > 0}
			<CommandSeparator />
			<CommandGroup heading="Drafts">
				{#each draftResults as draft}
					<CommandItem
						value="draft:{draft.id}"
						onSelect={() => navigate("/drafts")}
						class="flex items-center gap-2.5 text-sm"
					>
						<Search class="size-4 shrink-0 text-[var(--foreground-subtle)]" />
						<span class="truncate text-[var(--foreground-muted)]">
							{draft.platform} · {draft.content.slice(0, 60)}…
						</span>
					</CommandItem>
				{/each}
			</CommandGroup>
		{/if}
	</CommandList>
</CommandDialog>
