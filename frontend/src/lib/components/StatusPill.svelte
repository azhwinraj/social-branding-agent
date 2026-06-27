<script lang="ts">
	import { cn } from "$lib/utils.js";

	type Status = "connected" | "generating" | "needs-attention" | "pending";

	interface Props {
		status: Status;
		label?: string;
		class?: string;
	}

	let { status, label, class: className }: Props = $props();

	const config: Record<Status, { dot: string; pill: string }> = {
		connected: {
			dot: "bg-[var(--success)]",
			pill: "bg-[var(--success-soft)] text-[var(--success)]",
		},
		generating: {
			dot: "bg-[var(--warning)] animate-pulse",
			pill: "bg-[var(--warning-soft)] text-[var(--warning)]",
		},
		"needs-attention": {
			dot: "bg-[var(--danger)]",
			pill: "bg-[var(--danger-soft)] text-[var(--danger)]",
		},
		pending: {
			dot: "bg-[var(--foreground-subtle)]",
			pill: "border border-[var(--border)] text-[var(--foreground-muted)]",
		},
	};

	const defaultLabels: Record<Status, string> = {
		connected: "connected",
		generating: "generating",
		"needs-attention": "needs attention",
		pending: "pending",
	};

	const c = $derived(config[status]);
	const resolvedLabel = $derived(label ?? defaultLabels[status]);
</script>

<span class={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium", c.pill, className)}>
	<span class={cn("size-1.5 rounded-full", c.dot)}></span>
	{resolvedLabel}
</span>
