<script>
  export let snapshots = [];
  export let activeSnapshot = null;
  export let activeIndex = -1;
  export let isPlaying = false;
  export let canStepBackward = false;
  export let canStepForward = false;
  export let onSelectIndex = () => {};
  export let onReturnToLive = () => {};
  export let onStepBackward = () => {};
  export let onStepForward = () => {};
  export let onTogglePlayback = () => {};

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

    <div class="replay-header-actions">
      <span class="count-pill">{snapshots.length}</span>
      {#if activeSnapshot}
        <button class="live-button" type="button" on:click={onReturnToLive}>Back to live</button>
      {/if}
    </div>
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

    <div class="timeline-controls">
      <button
        class="control-button"
        type="button"
        title="Move one snapshot backward"
        disabled={!canStepBackward}
        on:click={onStepBackward}
      >
        Step back
      </button>
      <button
        class="control-button primary"
        type="button"
        title={isPlaying ? "Pause replay playback" : "Play recorded snapshots in sequence"}
        on:click={onTogglePlayback}
      >
        {#if isPlaying}
          Pause
        {:else}
          Play
        {/if}
      </button>
      <button
        class="control-button"
        type="button"
        title="Move one snapshot forward"
        disabled={!canStepForward}
        on:click={onStepForward}
      >
        Step forward
      </button>
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

  .replay-header-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    align-items: center;
    justify-content: flex-end;
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
    padding: 0.62rem 0.92rem;
    font: inherit;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .count-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    padding: 0.32rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
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
    accent-color: #f5b908;
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

  .timeline-controls {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .control-button {
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    padding: 0.82rem 0.86rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .control-button.primary {
    border: 0;
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
  }

  .control-button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  @media (max-width: 720px) {
    .replay-header,
    .timeline-meta {
      display: grid;
    }
  }
</style>
