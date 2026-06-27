<script lang="ts">
	import { cn } from "$lib/utils.js";

	type Platform = "linkedin" | "x" | "medium";

	interface Props {
		platform: Platform;
		class?: string;
	}

	let { platform, class: className }: Props = $props();

	const config: Record<Platform, { label: string }> = {
		linkedin: { label: "LinkedIn" },
		x: { label: "X" },
		medium: { label: "Medium" },
	};
</script>

<span
	class={cn(
		"inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--background-overlay)] px-2 py-1 text-xs font-medium text-[var(--foreground-muted)]",
		className
	)}
>
	<!-- Platform icon at 14px in brand color -->
	{#if platform === "linkedin"}
		<!-- LinkedIn "in" mark — brand blue #0A66C2 -->
		<svg
			width="14"
			height="14"
			viewBox="0 0 24 24"
			fill="#0A66C2"
			aria-hidden="true"
		>
			<path
				d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
			/>
		</svg>
	{:else if platform === "x"}
		<!-- X logo — renders in foreground-muted (monochrome brand) -->
		<svg
			width="14"
			height="14"
			viewBox="0 0 24 24"
			fill="currentColor"
			aria-hidden="true"
		>
			<path
				d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.748l7.73-8.835L2.314 2.25h7.178l4.157 5.498L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z"
			/>
		</svg>
	{:else}
		<!-- Medium "M" mark — renders in foreground-muted -->
		<svg
			width="14"
			height="14"
			viewBox="0 0 24 24"
			fill="currentColor"
			aria-hidden="true"
		>
			<path
				d="M13.54 12a6.8 6.8 0 0 1-6.77 6.82A6.8 6.8 0 0 1 0 12a6.8 6.8 0 0 1 6.77-6.82A6.8 6.8 0 0 1 13.54 12zm7.42 0c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42M24 12c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75C23.47 6.25 24 8.83 24 12z"
			/>
		</svg>
	{/if}
	{config[platform].label}
</span>
