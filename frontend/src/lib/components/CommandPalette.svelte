<script lang="ts">
	import { goto } from "$app/navigation";
	import { toggleMode, mode } from "mode-watcher";
	import { listDrafts, type SavedDraft } from "$lib/api.js";
	import {
		CommandDialog,
		CommandInput,
		CommandList,
		CommandEmpty,
		CommandGroup,
		CommandItem,
		CommandSeparator,
		CommandShortcut,
	} from "$lib/components/ui/command/index.js";
	import PenLine from "@lucide/svelte/icons/pen-line";
	import Layers from "@lucide/svelte/icons/layers";
	import Clock from "@lucide/svelte/icons/clock";
	import History from "@lucide/svelte/icons/history";
	import LayoutDashboard from "@lucide/svelte/icons/layout-dashboard";
	import Moon from "@lucide/svelte/icons/moon";
	import Sun from "@lucide/svelte/icons/sun";
	import Settings from "@lucide/svelte/icons/settings";
	import FileText from "@lucide/svelte/icons/file-text";

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	let searchValue = $state("");
	let allDrafts = $state<SavedDraft[]>([]);
	let loadingDrafts = $state(false);

	// Load drafts the first time the palette opens
	let draftsLoaded = $state(false);
	$effect(() => {
		if (open && !draftsLoaded) {
			draftsLoaded = true;
			loadingDrafts = true;
			listDrafts()
				.then((d) => (allDrafts = d))
				.catch(() => {})
				.finally(() => (loadingDrafts = false));
		}
	});

	// Client-side draft search — matches content or platform
	const matchingDrafts = $derived(
		searchValue.trim().length < 2
			? []
			: allDrafts
					.filter(
						(d) =>
							d.content.toLowerCase().includes(searchValue.toLowerCase()) ||
							d.platform.toLowerCase().includes(searchValue.toLowerCase())
					)
					.slice(0, 5)
	);

	// Always show navigation and action items regardless of search term.
	// Draft items are only rendered when matchingDrafts is non-empty.
	function commandFilter(value: string, _search: string): number {
		if (value.startsWith("nav:") || value.startsWith("action:")) return 1;
		return 1; // draft items: already pre-filtered before rendering
	}

	function run(action: () => void) {
		open = false;
		action();
	}

	const navItems = [
		{ value: "nav:compose", label: "Compose new post", href: "/", icon: PenLine, shortcut: "⌘1" },
		{ value: "nav:drafts", label: "View drafts", href: "/drafts", icon: Layers, shortcut: "⌘2" },
		{ value: "nav:queue", label: "View queue", href: "/queue", icon: Clock, shortcut: "⌘3" },
		{ value: "nav:history", label: "View history", href: "/history", icon: History, shortcut: "⌘4" },
		{ value: "nav:stats", label: "View stats", href: "/stats", icon: LayoutDashboard, shortcut: "⌘5" },
	];
</script>

<CommandDialog
	bind:open
	bind:value={searchValue}
	filter={commandFilter}
	title="Command Palette"
	description="Navigate or search drafts"
>
	<CommandInput placeholder="Search drafts or jump to…" />
	<CommandList>
		<CommandEmpty>
			{loadingDrafts ? "Loading drafts…" : "No results found."}
		</CommandEmpty>

		<!-- ── Navigation ─────────────────────────── -->
		<CommandGroup heading="Navigation">
			{#each navItems as item}
				<CommandItem value={item.value} onSelect={() => run(() => goto(item.href))}>
					<item.icon class="size-4 text-[var(--foreground-subtle)]" />
					{item.label}
					<CommandShortcut>{item.shortcut}</CommandShortcut>
				</CommandItem>
			{/each}
		</CommandGroup>

		<!-- ── Actions ────────────────────────────── -->
		<CommandSeparator />
		<CommandGroup heading="Actions">
			<CommandItem value="action:theme" onSelect={() => run(toggleMode)}>
				{#if mode.current === "dark"}
					<Moon class="size-4 text-[var(--foreground-subtle)]" />
					Switch to light mode
				{:else}
					<Sun class="size-4 text-[var(--foreground-subtle)]" />
					Switch to dark mode
				{/if}
				<CommandShortcut>⌘D</CommandShortcut>
			</CommandItem>
			<CommandItem value="action:settings" onSelect={() => run(() => {})}>
				<Settings class="size-4 text-[var(--foreground-subtle)]" />
				Open settings
			</CommandItem>
		</CommandGroup>

		<!-- ── Draft search results ───────────────── -->
		{#if matchingDrafts.length > 0}
			<CommandSeparator />
			<CommandGroup heading="Drafts">
				{#each matchingDrafts as draft (draft.id)}
					<CommandItem
						value={`draft:${draft.id}`}
						onSelect={() => run(() => goto("/drafts"))}
					>
						<FileText class="size-4 shrink-0 text-[var(--foreground-subtle)]" />
						<span class="truncate">
							<span class="text-[var(--foreground-subtle)] capitalize mr-1.5"
								>{draft.platform}</span
							>{draft.content.slice(0, 72)}{draft.content.length > 72 ? "…" : ""}
						</span>
					</CommandItem>
				{/each}
			</CommandGroup>
		{/if}
	</CommandList>
</CommandDialog>
