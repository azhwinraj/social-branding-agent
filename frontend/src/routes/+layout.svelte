<script lang="ts">
	import "../app.css";
	import { ModeWatcher, mode, toggleMode } from "mode-watcher";
	import { page } from "$app/state";
	import { browser } from "$app/environment";
	import { cn } from "$lib/utils.js";
	import Moon from "@lucide/svelte/icons/moon";
	import Sun from "@lucide/svelte/icons/sun";
	import Settings from "@lucide/svelte/icons/settings";

	let { children } = $props();

	// Bridge mode-watcher's class-based mode → our data-theme attribute.
	// The static data-theme="dark" in app.html covers SSR; this takes over on hydration.
	$effect(() => {
		if (browser) {
			document.documentElement.setAttribute("data-theme", $mode ?? "dark");
		}
	});

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

<ModeWatcher defaultMode="dark" />

<div class="min-h-screen bg-background text-foreground">
	<!-- ─── Sticky nav ─────────────────────────────────────────── -->
	<header
		class="sticky top-0 z-50 h-14 border-b border-[var(--border)] bg-background/80 backdrop-blur-md"
	>
		<div class="mx-auto flex h-full max-w-7xl items-center gap-4 px-6">
			<!-- Logo -->
			<a
				href="/"
				class="flex shrink-0 items-center gap-2.5 text-sm font-medium text-foreground"
			>
				<!-- Diamond mark in primary (electric violet) -->
				<div class="size-[18px] rotate-45 rounded-[3px] bg-primary"></div>
				Social Branding Agent
			</a>

			<!-- Nav links -->
			<nav class="flex items-center gap-0.5" aria-label="Main navigation">
				{#each navLinks as link}
					<a
						href={link.href}
						class={cn(
							"rounded-md px-3 py-1.5 text-sm transition-colors",
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
				<!-- ⌘K trigger — command palette wired in PR #5 -->
				<button
					class="flex h-7 items-center gap-1.5 rounded-md border border-[var(--border)] px-2.5 text-xs text-[var(--foreground-subtle)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--foreground-muted)]"
					aria-label="Open command palette (⌘K)"
				>
					<span>Search</span>
					<kbd class="font-mono text-[10px] opacity-60">⌘K</kbd>
				</button>

				<!-- Theme toggle -->
				<button
					onclick={toggleMode}
					class="flex size-8 items-center justify-center rounded-md text-[var(--foreground-muted)] transition-colors hover:bg-[var(--background-overlay)] hover:text-foreground"
					aria-label="Toggle theme"
				>
					{#if $mode === "dark"}
						<Moon class="size-4" />
					{:else}
						<Sun class="size-4" />
					{/if}
				</button>

				<!-- Settings (placeholder for future settings page) -->
				<button
					class="flex size-8 items-center justify-center rounded-md text-[var(--foreground-muted)] transition-colors hover:bg-[var(--background-overlay)] hover:text-foreground"
					aria-label="Settings"
				>
					<Settings class="size-4" />
				</button>

				<!-- User avatar initials -->
				<div
					class="flex size-7 items-center justify-center rounded-full bg-[var(--background-overlay)] text-[11px] font-medium text-[var(--foreground-muted)] select-none"
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
