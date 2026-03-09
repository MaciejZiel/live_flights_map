<script>
  export let snapshots = [];
  export let activeSnapshot = null;
  export let activeIndex = -1;
  export let onSelectIndex = () => {};
  export let onReturnToLive = () => {};

  function handleInput(event) {
    onSelectIndex(Number(event.currentTarget.value));
  }

  function formatSnapshotTime(value) {
    return new Intl.DateTimeFormat("pl-PL", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(value));
  }

  $: sliderValue = activeIndex >= 0 ? activeIndex : Math.max(0, snapshots.length - 1);
</script>

<section class="panel replay-panel">
  <div class="replay-header">
    <div>
      <p class="eyebrow">Session history</p>
      <h2>Replay timeline</h2>
    </div>

    {#if activeSnapshot}
      <button class="live-button" type="button" on:click={onReturnToLive}>Back to live</button>
    {/if}
  </div>

  {#if snapshots.length < 2}
    <p>Collecting snapshots. Replay becomes available after the second update.</p>
  {:else}
    <label class="timeline-field">
      <span>{activeSnapshot ? "Inspecting recorded snapshot" : "Following the live tail"}</span>
      <input
        type="range"
        min="0"
        max={snapshots.length - 1}
        step="1"
        value={sliderValue}
        on:input={handleInput}
      />
    </label>

    <div class="timeline-meta">
      <strong>{formatSnapshotTime(snapshots[sliderValue].fetchedAt)}</strong>
      <span>{snapshots[sliderValue].count} tracked aircraft</span>
    </div>
  {/if}
</section>

<style>
  .replay-panel {
    display: grid;
    gap: 0.9rem;
  }

  .replay-header {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 1rem;
  }

  .eyebrow {
    margin: 0 0 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.72rem;
    color: var(--color-muted);
  }

  h2,
  p {
    margin: 0;
  }

  .live-button {
    border: 1px solid var(--surface-border);
    border-radius: 999px;
    padding: 0.45rem 0.75rem;
    font: inherit;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .timeline-field {
    display: grid;
    gap: 0.55rem;
  }

  .timeline-field span {
    font-size: 0.83rem;
    font-weight: 600;
    color: var(--color-muted);
  }

  .timeline-field input {
    width: 100%;
  }

  .timeline-meta {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    font-size: 0.9rem;
  }

  .timeline-meta span {
    color: var(--color-muted);
  }

  @media (max-width: 720px) {
    .replay-header,
    .timeline-meta {
      display: grid;
    }
  }
</style>
