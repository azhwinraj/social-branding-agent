<script lang="ts">
	import { healthCheck, generate, type Draft } from "$lib/api.js";
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { cn, snakeCaseToTitleCase } from "$lib/utils.js";
	import StatusPill from "$lib/components/StatusPill.svelte";
	import PlatformBadge from "$lib/components/PlatformBadge.svelte";
	import TypeBadge from "$lib/components/TypeBadge.svelte";
	import { Skeleton } from "$lib/components/ui/skeleton/index.js";
	import ImageIcon from "@lucide/svelte/icons/image";
	import XIcon from "@lucide/svelte/icons/x";
	import Zap from "@lucide/svelte/icons/zap";
	import Gauge from "@lucide/svelte/icons/gauge";
	import Sparkles from "@lucide/svelte/icons/sparkles";
	import TriangleAlert from "@lucide/svelte/icons/triangle-alert";
	import ArrowRight from "@lucide/svelte/icons/arrow-right";
	import RotateCcw from "@lucide/svelte/icons/rotate-ccw";

	// ── Types ─────────────────────────────────────────────────────────
	type DraftWithWarning = Draft & { adherence_warning?: boolean };
	type GenMode = "fast" | "balanced" | "polish";
	type Research = "auto" | "on" | "off";

	// ── State ─────────────────────────────────────────────────────────
	let backendStatus = $state<"checking" | "ok" | "error">("checking");
	let context = $state("");
	let selectedPlatforms = $state<string[]>(["linkedin", "x", "medium"]);
	let genMode = $state<GenMode>("balanced");
	let research = $state<Research>("auto");
	let imageFile = $state<File | null>(null);
	let imagePreviewUrl = $state<string | null>(null);
	let isDragOver = $state(false);
	let loading = $state(false);
	let drafts = $state<DraftWithWarning[]>([]);
	let routerReasoning = $state<string | null>(null);
	let postTypes = $state<Record<string, string>>({});
	let runId = $state<string | null>(null);
	let error = $state<string | null>(null);
	let textareaEl = $state<HTMLTextAreaElement | null>(null);

	// ── Auto-resize textarea ──────────────────────────────────────────
	$effect(() => {
		const _ = context;
		if (textareaEl) {
			textareaEl.style.height = "auto";
			textareaEl.style.height = `${Math.max(180, textareaEl.scrollHeight)}px`;
		}
	});

	// ── Health check ──────────────────────────────────────────────────
	onMount(async () => {
		try {
			await healthCheck();
			backendStatus = "ok";
		} catch {
			backendStatus = "error";
		}
	});

	// ── Image handling ─────────────────────────────────────────────────
	function setImage(file: File) {
		imageFile = file;
		imagePreviewUrl = URL.createObjectURL(file);
	}

	function clearImage() {
		if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
		imageFile = null;
		imagePreviewUrl = null;
	}

	function handleFileDrop(e: DragEvent) {
		e.preventDefault();
		isDragOver = false;
		const file = e.dataTransfer?.files?.[0];
		if (file && file.type.startsWith("image/")) setImage(file);
	}

	function handleFileInput(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (file) setImage(file);
	}

	// ── Platform toggle ───────────────────────────────────────────────
	function togglePlatform(p: string) {
		if (selectedPlatforms.includes(p)) {
			if (selectedPlatforms.length > 1) selectedPlatforms = selectedPlatforms.filter((x) => x !== p);
		} else {
			selectedPlatforms = [...selectedPlatforms, p];
		}
	}

	// ── Generate ──────────────────────────────────────────────────────
	async function handleGenerate() {
		if (!context.trim() || selectedPlatforms.length === 0 || loading) return;
		loading = true;
		drafts = [];
		error = null;
		runId = null;
		routerReasoning = null;
		postTypes = {};
		try {
			const imageDesc = imageFile
				? `${imageFile.name} (${(imageFile.size / 1024 / 1024).toFixed(1)} MB)`
				: undefined;
			const data = await generate(context, selectedPlatforms, imageDesc, research, genMode);
			drafts = data.drafts as DraftWithWarning[];
			runId = data.run_id;
			routerReasoning = data.router_reasoning;
			postTypes = data.post_types ?? {};
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
			e.preventDefault();
			handleGenerate();
		}
	}

	function reset() {
		drafts = [];
		error = null;
		runId = null;
		routerReasoning = null;
		postTypes = {};
	}

	// ── Derived ───────────────────────────────────────────────────────
	const canGenerate = $derived(context.trim().length > 0 && selectedPlatforms.length > 0 && !loading);
	const totalTokens = $derived(drafts.reduce((s, d) => s + d.prompt_tokens + d.completion_tokens, 0));
	const totalCost = $derived(drafts.reduce((s, d) => s + d.cost_usd, 0));

	const backendStatusState = $derived(
		backendStatus === "ok" ? "connected" : backendStatus === "error" ? "needs-attention" : "pending"
	);
	const backendLabel = $derived(
		backendStatus === "ok" ? "Backend connected" :
		backendStatus === "error" ? "Backend unreachable" :
		"Connecting…"
	);

	const modeOptions: { value: GenMode; icon: typeof Zap; label: string; hint?: string }[] = [
		{ value: "fast", icon: Zap, label: "Fast", hint: "Llama 3.1-8B only — instant and free, lower quality." },
		{ value: "balanced", icon: Gauge, label: "Balanced" },
		{ value: "polish", icon: Sparkles, label: "Polish", hint: "Claude Haiku as Tier 1 — higher quality, small cost." },
	];

	const researchOptions: { value: Research; label: string }[] = [
		{ value: "auto", label: "Auto" },
		{ value: "on", label: "On" },
		{ value: "off", label: "Off" },
	];

	const platformOptions = [
		{
			value: "linkedin" as const,
			label: "LinkedIn",
			svg: `<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>`,
			iconColor: "#0A66C2",
		},
		{
			value: "x" as const,
			label: "X",
			svg: `<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.748l7.73-8.835L2.314 2.25h7.178l4.157 5.498L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z"/>`,
			iconColor: "currentColor",
		},
		{
			value: "medium" as const,
			label: "Medium",
			svg: `<path d="M13.54 12a6.8 6.8 0 0 1-6.77 6.82A6.8 6.8 0 0 1 0 12a6.8 6.8 0 0 1 6.77-6.82A6.8 6.8 0 0 1 13.54 12zm7.42 0c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42M24 12c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75C23.47 6.25 24 8.83 24 12z"/>`,
			iconColor: "currentColor",
		},
	];

	const modeHint = $derived(modeOptions.find((m) => m.value === genMode)?.hint ?? null);
</script>

<div class="space-y-6">
	<!-- ── Status pill ───────────────────────────────────────────────── -->
	<StatusPill status={backendStatusState} label={backendLabel} />

	<!-- ── Page heading ──────────────────────────────────────────────── -->
	<div>
		<h1 class="text-3xl font-semibold text-foreground">Compose</h1>
		<p class="mt-1 text-sm text-[var(--foreground-muted)]">
			Paste your context and get platform-specific drafts.
		</p>
	</div>

	<!-- ══════════════════════════════════════════════════════════════════
	     LOADING STATE — skeleton cards while generating
	     ══════════════════════════════════════════════════════════════════ -->
	{#if loading}
		<div class="space-y-4">
			{#if routerReasoning}
				<p class="text-xs text-[var(--foreground-muted)] font-mono px-1">{routerReasoning}</p>
			{/if}
			{#each selectedPlatforms as p}
				<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-5 space-y-4">
					<div class="flex items-center justify-between">
						<Skeleton class="h-6 w-24 rounded-md" />
						<Skeleton class="h-4 w-20 rounded" />
					</div>
					<div class="space-y-2.5">
						<Skeleton class="h-4 w-full rounded" />
						<Skeleton class="h-4 w-full rounded" />
						<Skeleton class="h-4 w-4/5 rounded" />
						<Skeleton class="h-4 w-3/4 rounded" />
						<Skeleton class="h-4 w-2/3 rounded" />
					</div>
				</div>
			{/each}
		</div>

	<!-- ══════════════════════════════════════════════════════════════════
	     RESULTS STATE — generated draft cards
	     ══════════════════════════════════════════════════════════════════ -->
	{:else if drafts.length > 0}
		<div class="space-y-4">
			<!-- Meta row -->
			<div class="flex items-center justify-between">
				<p class="text-xs text-[var(--foreground-subtle)]">
					{drafts.length} draft{drafts.length > 1 ? "s" : ""} ·
					{totalTokens.toLocaleString()} tokens ·
					<span class="font-mono numeric">${totalCost.toFixed(6)}</span>
					{#if runId}<span class="ml-2 font-mono opacity-50">run:{runId.slice(0, 8)}</span>{/if}
				</p>
				<button
					onclick={reset}
					class="inline-flex items-center gap-1.5 text-xs text-[var(--foreground-muted)] hover:text-foreground transition-colors"
				>
					<RotateCcw class="size-3" />
					Generate again
				</button>
			</div>

			<!-- Router reasoning -->
			{#if routerReasoning}
				<p class="text-xs text-[var(--foreground-subtle)] font-mono px-1">{routerReasoning}</p>
			{/if}

			<!-- Error -->
			{#if error}
				<div class="flex items-start gap-2.5 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]">
					<TriangleAlert class="mt-0.5 size-4 shrink-0" />
					{error}
				</div>
			{/if}

			<!-- Draft cards -->
			{#each drafts as draft}
				<div class="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] overflow-hidden">
					<!-- Card header -->
					<div class="flex items-center justify-between border-b border-[var(--border)] px-5 py-3">
						<div class="flex items-center gap-2">
							<PlatformBadge platform={draft.platform as "linkedin" | "x" | "medium"} />
							{#if postTypes[draft.platform]}
								<TypeBadge type={postTypes[draft.platform]} />
							{/if}
						</div>
						<span class="text-xs text-[var(--foreground-subtle)] font-mono numeric">
							{(draft.prompt_tokens + draft.completion_tokens).toLocaleString()} tok ·
							${draft.cost_usd.toFixed(6)} · {draft.model.split("/").pop()}
						</span>
					</div>
					<!-- Draft content -->
					<div class="px-5 py-4 text-sm leading-7 text-foreground whitespace-pre-wrap">
						{draft.content}
					</div>
					<!-- Adherence warning -->
					{#if draft.adherence_warning}
						<div class="mx-5 mb-4 flex items-center gap-2 rounded-lg bg-[var(--warning-soft)] px-3 py-2 text-xs text-[var(--warning)]">
							<TriangleAlert class="size-3.5 shrink-0" />
							Adherence check flagged — review carefully before publishing.
						</div>
					{/if}
				</div>
			{/each}

			<!-- CTA to drafts page -->
			<div class="pt-2 text-center">
				<button
					onclick={() => goto("/drafts")}
					class="inline-flex items-center gap-1.5 text-sm text-primary hover:opacity-80 transition-opacity font-medium"
				>
					Refine, approve, or schedule in Drafts
					<ArrowRight class="size-4" />
				</button>
			</div>
		</div>

	<!-- ══════════════════════════════════════════════════════════════════
	     FORM STATE — compose form (idle)
	     ══════════════════════════════════════════════════════════════════ -->
	{:else}
		<div class="space-y-4">
			<!-- Error (from a failed previous generate) -->
			{#if error}
				<div class="flex items-start gap-2.5 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]">
					<TriangleAlert class="mt-0.5 size-4 shrink-0" />
					{error}
				</div>
			{/if}

			<!-- Textarea -->
			<textarea
				bind:this={textareaEl}
				bind:value={context}
				onkeydown={handleKeydown}
				placeholder="What do you want to post about? Paste a GitHub README, a project update, a lesson learned — anything."
				class="w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] px-4 py-3.5 text-sm text-foreground leading-relaxed placeholder:text-[var(--foreground-subtle)] outline-none transition-shadow focus:shadow-[0_0_0_2px_var(--primary-soft)] focus:border-[var(--border-strong)]"
				style="min-height:180px"
			></textarea>

			<!-- Image drop zone -->
			<div
				role="button"
				tabindex="0"
				class={cn(
					"rounded-xl border-2 border-dashed px-6 py-5 transition-colors cursor-pointer",
					isDragOver
						? "border-primary bg-[var(--primary-soft)]"
						: "border-[var(--border)] hover:border-[var(--border-strong)]"
				)}
				ondragover={(e) => { e.preventDefault(); isDragOver = true; }}
				ondragleave={() => (isDragOver = false)}
				ondrop={handleFileDrop}
				onkeydown={(e) => e.key === "Enter" && document.getElementById("file-input")?.click()}
			>
				{#if imageFile && imagePreviewUrl}
					<div class="flex items-center gap-3">
						<img src={imagePreviewUrl} alt="Preview" class="size-12 rounded-lg object-cover shrink-0" />
						<div class="min-w-0">
							<p class="text-sm font-medium text-foreground truncate">{imageFile.name}</p>
							<p class="text-xs text-[var(--foreground-subtle)]">
								{(imageFile.size / 1024 / 1024).toFixed(1)} MB
							</p>
						</div>
						<button
							onclick={(e) => { e.stopPropagation(); clearImage(); }}
							class="ml-auto flex size-7 items-center justify-center rounded-lg text-[var(--foreground-muted)] hover:bg-[var(--background-overlay)] hover:text-foreground transition-colors shrink-0"
							aria-label="Remove image"
						>
							<XIcon class="size-4" />
						</button>
					</div>
				{:else}
					<label class="flex flex-col items-center gap-2 cursor-pointer">
						<ImageIcon class="size-7 text-[var(--foreground-subtle)]" />
						<span class="text-sm text-[var(--foreground-muted)]">
							Drop an image or <span class="text-foreground underline underline-offset-2">click to upload</span>
						</span>
						<span class="text-xs text-[var(--foreground-subtle)]">PNG, JPG up to 10 MB · optional</span>
						<input
							id="file-input"
							type="file"
							accept="image/*"
							class="sr-only"
							onchange={handleFileInput}
						/>
					</label>
				{/if}
			</div>

			<!-- Mode + Research row -->
			<div class="flex flex-wrap items-center gap-4">
				<!-- Mode -->
				<div class="flex items-center gap-2.5">
					<span class="text-xs text-[var(--foreground-subtle)] w-14 shrink-0">Mode</span>
					<div class="flex overflow-hidden rounded-lg border border-[var(--border)]">
						{#each modeOptions as opt}
							<button
								onclick={() => (genMode = opt.value)}
								class={cn(
									"flex items-center gap-1.5 border-r border-[var(--border)] px-3 py-1.5 text-xs font-medium transition-colors last:border-r-0",
									genMode === opt.value
										? "bg-[var(--primary-soft)] text-primary"
										: "text-[var(--foreground-muted)] hover:bg-[var(--background-overlay)] hover:text-foreground"
								)}
							>
								<opt.icon class="size-3" />
								{opt.label}
							</button>
						{/each}
					</div>
				</div>

				<!-- Research -->
				<div class="flex items-center gap-2.5">
					<span class="text-xs text-[var(--foreground-subtle)] w-14 shrink-0">Research</span>
					<div class="flex overflow-hidden rounded-lg border border-[var(--border)]">
						{#each researchOptions as opt}
							<button
								onclick={() => (research = opt.value)}
								class={cn(
									"border-r border-[var(--border)] px-3 py-1.5 text-xs font-medium transition-colors last:border-r-0",
									research === opt.value
										? "bg-[var(--primary-soft)] text-primary"
										: "text-[var(--foreground-muted)] hover:bg-[var(--background-overlay)] hover:text-foreground"
								)}
							>
								{opt.label}
							</button>
						{/each}
					</div>
				</div>
			</div>

			<!-- Mode hint -->
			{#if modeHint}
				<p class="text-xs text-[var(--foreground-subtle)] -mt-1">{modeHint}</p>
			{/if}

			<!-- Platform chips -->
			<div>
				<p class="mb-2 text-xs text-[var(--foreground-subtle)]">Platforms</p>
				<div class="flex gap-2">
					{#each platformOptions as opt}
						{@const isSelected = selectedPlatforms.includes(opt.value)}
						<button
							onclick={() => togglePlatform(opt.value)}
							class={cn(
								"inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-medium transition-all",
								isSelected
									? "border-primary bg-[var(--primary-soft)] text-foreground"
									: "border-[var(--border)] text-[var(--foreground-muted)] hover:border-[var(--border-strong)] hover:text-foreground"
							)}
						>
							<svg width="14" height="14" viewBox="0 0 24 24" fill={opt.iconColor} aria-hidden="true">
								{@html opt.svg}
							</svg>
							{opt.label}
						</button>
					{/each}
				</div>
			</div>

			<!-- Generate button -->
			<button
				onclick={handleGenerate}
				disabled={!canGenerate}
				class="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground transition-all hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
			>
				Generate Drafts
				<kbd class="ml-auto font-mono text-[11px] opacity-60">⌘↵</kbd>
			</button>

			<p class="text-center text-xs text-[var(--foreground-subtle)]">
				Drafts typically generate in 5–8 seconds.
			</p>
		</div>
	{/if}
</div>
