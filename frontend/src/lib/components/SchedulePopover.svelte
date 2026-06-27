<script lang="ts">
	import {
		Popover,
		PopoverTrigger,
		PopoverContent,
	} from "$lib/components/ui/popover/index.js";
	import { scheduleDraft } from "$lib/api.js";
	import { cn } from "$lib/utils.js";
	import CalendarIcon from "@lucide/svelte/icons/calendar";
	import CheckIcon from "@lucide/svelte/icons/check";
	import TriangleAlert from "@lucide/svelte/icons/triangle-alert";

	interface Props {
		draftId: number;
		disabled?: boolean;
		onScheduled: (scheduledAt: Date) => void;
	}

	let { draftId, disabled = false, onScheduled }: Props = $props();

	let open = $state(false);
	let scheduling = $state(false);
	let scheduleError = $state<string | null>(null);

	// Default: tomorrow at 9:00 AM
	function defaultDate(): string {
		const d = new Date(Date.now() + 24 * 60 * 60 * 1000);
		const pad = (n: number) => String(n).padStart(2, "0");
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
	}

	let dateVal = $state(defaultDate());
	let timeVal = $state("09:00");

	// Minimum date = today
	const today = new Date();
	const pad = (n: number) => String(n).padStart(2, "0");
	const minDate = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;

	const isValid = $derived(Boolean(dateVal && timeVal));

	async function handleSchedule() {
		if (!isValid || scheduling) return;
		scheduling = true;
		scheduleError = null;
		try {
			const dt = new Date(`${dateVal}T${timeVal}`);
			await scheduleDraft(draftId, dt);
			open = false;
			onScheduled(dt);
		} catch (e) {
			scheduleError = (e as Error).message;
		} finally {
			scheduling = false;
		}
	}
</script>

<Popover bind:open>
	<PopoverTrigger
		{disabled}
		class={cn(
			"inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 text-xs font-medium text-[var(--foreground-muted)] transition-colors",
			"hover:border-[var(--border-strong)] hover:text-foreground",
			"disabled:cursor-not-allowed disabled:opacity-40"
		)}
	>
		<CalendarIcon class="size-3.5" />
		Schedule
	</PopoverTrigger>

	<PopoverContent
		class="w-72 rounded-xl border border-[var(--border)] bg-[var(--background-overlay)] p-4 shadow-lg"
		align="start"
	>
		<p class="mb-3 text-sm font-medium text-foreground">Schedule post</p>

		<div class="space-y-3">
			<!-- Date -->
			<div class="space-y-1.5">
				<label class="text-xs text-[var(--foreground-subtle)]" for="sched-date-{draftId}">
					Date
				</label>
				<input
					id="sched-date-{draftId}"
					type="date"
					bind:value={dateVal}
					min={minDate}
					class="w-full rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] px-3 py-1.5 text-sm text-foreground outline-none focus:border-[var(--border-strong)] focus:shadow-[0_0_0_2px_var(--primary-soft)] transition-shadow [color-scheme:dark]"
				/>
			</div>

			<!-- Time -->
			<div class="space-y-1.5">
				<label class="text-xs text-[var(--foreground-subtle)]" for="sched-time-{draftId}">
					Time
				</label>
				<input
					id="sched-time-{draftId}"
					type="time"
					bind:value={timeVal}
					class="w-full rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] px-3 py-1.5 text-sm text-foreground outline-none focus:border-[var(--border-strong)] focus:shadow-[0_0_0_2px_var(--primary-soft)] transition-shadow [color-scheme:dark]"
				/>
			</div>

			<!-- Error -->
			{#if scheduleError}
				<div class="flex items-start gap-2 rounded-lg bg-[var(--danger-soft)] px-3 py-2 text-xs text-[var(--danger)]">
					<TriangleAlert class="mt-0.5 size-3.5 shrink-0" />
					{scheduleError}
				</div>
			{/if}

			<!-- Confirm button -->
			<button
				onclick={handleSchedule}
				disabled={!isValid || scheduling}
				class="flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
			>
				{#if scheduling}
					<span class="size-3.5 animate-spin rounded-full border border-white/20 border-t-white"></span>
					Scheduling…
				{:else}
					<CheckIcon class="size-3.5" />
					Confirm
				{/if}
			</button>
		</div>
	</PopoverContent>
</Popover>
