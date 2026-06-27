<script lang="ts">
	import "../app.css";
	import { ModeWatcher, mode, toggleMode } from "mode-watcher";
	import { page } from "$app/state";
	import { browser } from "$app/environment";
	import { onNavigate } from "$app/navigation";
	import { cn } from "$lib/utils.js";
	import CommandPalette from "$lib/components/CommandPalette.svelte";
	import Moon from "@lucide/svelte/icons/moon";
	import Sun from "@lucide/svelte/icons/sun";
	import Settings from "@lucide/svelte/icons/settings";

	let { children } = $props();

	// ── Theme bridge ───────────────────────────────────────────────
	// mode-watcher's `mode` is { readonly current: ... }, not a store.
	// Bridge to our data-theme attribute for OKLCH token switching.
	$effect(() => {
		if (browser) {
			document.documentElement.setAttribute("data-theme", mode.current ?? "dark");
		}
	});

	// ── Command palette ────────────────────────────────────────────
	let commandOpen = $state(false);

	// ── Keyboard shortcuts ─────────────────────────────────────────
	// ⌘K / Ctrl+K → palette  ⌘D → theme  ⌘1-5 → nav
	const NAV_HREFS = ["/", "/drafts", "/queue", "/history", "/stats"];

	function handleKeydown(e: KeyboardEvent) {
		const mod = e.metaKey || e.ctrlKey;
		if (!mod) return;

		switch (e.key) {
			case "k":
			case "K":
				e.preventDefault();
				commandOpen = !commandOpen;
				break;
			case "d":
			case "D":
				e.preventDefault();
				toggleMode();
				break;
			case "1":
			case "2":
			case "3":
			case "4":
			case "5": {
				const idx = parseInt(e.key) - 1;
				const href = NAV_HREFS[idx];
				if (href) {
					e.preventDefault();
					import("$app/navigation").then((m) => m.goto(href));
				}
				break;
			}
		}
	}

	// ── View transitions (Chrome 111+, progressive enhancement) ──
	onNavigate((navigation) => {
		if (!document.startViewTransition) return;
		return new Promise<void>((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});

	// ── Nav helpers ────────────────────────────────────────────────
	const navLinks = [
		{ href: "/", label: "Compose" },
		{ href: "/drafts", label: "Drafts" },
		{ href: "/queue", label: "Queue" },
		{ href: "/history", label: "History" },
		{ href: "/stats", label: "Stats" },
	];

	function isActive(href: string) {
		if (href === "/") return page.url.pathname === "/";
		return page.url.pathname.startsWith(href);
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<ModeWatcher defaultMode="dark" />
<CommandPalette bind:open={commandOpen} />

<div class="min-h-screen bg-background text-foreground">
	<!-- ─── Sticky nav ─────────────────────────────────────────── -->
	<header
		class="sticky top-0 z-50 h-14 border-b border-[var(--border)] bg-background/80 backdrop-blur-md"
	>
		<div class="mx-auto flex h-full max-w-7xl items-center gap-4 px-6">
			<!-- Logo -->
			<a
				href="/"
				class="flex shrink-0 items-center gap-2.5 text-sm font-medium text-foreground transition-opacity hover:opacity-80"
			>
				<div class="size-[18px] rotate-45 rounded-[3px] bg-primary"></div>
				Social Branding Agent
			</a>

			<!-- Nav links -->
			<nav class="flex items-center gap-0.5" aria-label="Main navigation">
				{#each navLinks as link}
					<a
						href={link.href}
						class={cn(
							"rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
							isActive(link.href)
								? "bg-[var(--primary-soft)] font-medium text-primary"
								: "text-[var(--foreground-muted)] hover:bg-[var(--background-overlay)] hover:text-foreground"
						)}
					>
						{link.label}
					</a>
				{/each}
			</nav>

			<!-- Right cluster -->
			<div class="ml-auto flex items-center gap-1">
				<!-- ⌘K trigger -->
				<button
					onclick={() => (commandOpen = true)}
					class="flex h-7 items-center gap-1.5 rounded-md border border-[var(--border)] px-2.5 text-xs text-[var(--foreground-subtle)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--foreground-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
					aria-label="Open command palette (⌘K)"
				>
					<span>Search</span>
					<kbd class="font-mono text-[10px] opacity-60">⌘K</kbd>
				</button>

				<!-- Theme toggle ⌘D -->
				<button
					onclick={toggleMode}
					class="flex size-8 items-center justify-center rounded-md text-[var(--foreground-muted)] transition-colors hover:bg-[var(--background-overlay)] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
					aria-label="Toggle theme (⌘D)"
					title="Toggle theme (⌘D)"
				>
					{#if mode.current === "dark"}
						<Moon class="size-4" />
					{:else}
						<Sun class="size-4" />
					{/if}
				</button>

				<!-- Settings stub -->
				<button
					class="flex size-8 items-center justify-center rounded-md text-[var(--foreground-muted)] transition-colors hover:bg-[var(--background-overlay)] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
					aria-label="Settings"
				>
					<Settings class="size-4" />
				</button>

				<!-- User avatar initials -->
				<div
					class="flex size-7 select-none items-center justify-center rounded-full bg-[var(--background-overlay)] text-[11px] font-medium text-[var(--foreground-muted)]"
				>
					AR
				</div>
			</div>
		</div>
	</header>

	<!-- ─── Page content ──────────────────────────────────────── -->
	<main class="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
		{@render children()}
	</main>
</div>
