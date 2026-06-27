<script lang="ts">
	import "../app.css";
	let { children } = $props();
</script>

<div class="shell">
	<nav>
		<span class="brand">Social Branding Agent</span>
		<a href="/">Compose</a>
		<a href="/drafts">Drafts</a>
		<a href="/queue">Queue</a>
		<a href="/history">History</a>
		<a href="/stats">Stats</a>
	</nav>
	<main>
		{@render children()}
	</main>
</div>

<style>
	:global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
	:global(body) { font-family: system-ui, sans-serif; background: #0f0f0f; color: #e5e5e5; }

	.shell { display: flex; flex-direction: column; min-height: 100vh; }

	nav {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		padding: 0.75rem 1.5rem;
		background: #1a1a1a;
		border-bottom: 1px solid #2a2a2a;
	}

	.brand { font-weight: 600; margin-right: auto; color: #fff; }

	nav a {
		color: #a3a3a3;
		text-decoration: none;
		font-size: 0.9rem;
	}

	nav a:hover { color: #fff; }

	main { flex: 1; padding: 2rem 1.5rem; max-width: 900px; width: 100%; margin: 0 auto; }
</style>
