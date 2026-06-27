<script lang="ts">
	import { cn, snakeCaseToTitleCase } from "$lib/utils.js";
	import ChevronDown from "@lucide/svelte/icons/chevron-down";

	interface Props {
		type: string;
		/** Show a ChevronDown — use when this badge acts as a dropdown trigger */
		asDropdown?: boolean;
		class?: string;
	}

	let { type, asDropdown = false, class: className }: Props = $props();

	const label = $derived(snakeCaseToTitleCase(type));
</script>

<span
	class={cn(
		"inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--background-overlay)] px-2 py-0.5 text-xs font-medium text-[var(--foreground-muted)]",
		className
	)}
>
	{label}
	{#if asDropdown}
		<ChevronDown class="size-3 opacity-60" />
	{/if}
</span>
