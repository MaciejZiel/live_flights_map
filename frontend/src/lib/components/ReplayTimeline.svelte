<script>
  export let snapshots = [];
  export let activeSnapshot = null;
  export let activeIndex = -1;
  export let isPlaying = false;
  export let playbackSpeed = 1;
  export let canStepBackward = false;
  export let canStepForward = false;
  export let onSelectIndex = () => {};
  export let onReturnToLive = () => {};
  export let onJumpStart = () => {};
  export let onJumpLatest = () => {};
  export let onSetPlaybackSpeed = () => {};
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

  function handleSpeedChange(event) {
    onSetPlaybackSpeed(Number(event.currentTarget.value));
  }

  $: sliderValue = activeIndex >= 0 ? activeIndex : Math.max(0, snapshots.length - 1);
  $: activeSnapshotLabel = snapshots[sliderValue] ? formatSnapshotTime(snapshots[sliderValue].fetchedAt) : "--:--";
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
      <strong>{activeSnapshotLabel}</strong>
      <span>{snapshots[sliderValue].count} tracked aircraft</span>
    </div>

    <div class="timeline-speed-row">
      <span>Playback speed</span>
      <select value={playbackSpeed} on:change={handleSpeedChange}>
        <option value="0.5">0.5x</option>
        <option value="1">1x</option>
        <option value="2">2x</option>
        <option value="4">4x</option>
      </select>
    </div>

    <div class="timeline-controls">
      <button class="control-button" type="button" on:click={onJumpStart}>First</button>
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
      <button class="control-button" type="button" on:click={onJumpLatest}>Latest</button>
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
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .timeline-speed-row {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .timeline-speed-row span {
    font-size: 0.8rem;
    color: var(--color-muted);
  }

  .timeline-speed-row select {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.56rem 0.72rem;
    font: inherit;
    color: var(--color-text);
    background: var(--surface-input-bg);
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
    .timeline-meta,
    .timeline-speed-row {
      display: grid;
    }

    .timeline-controls {
      grid-template-columns: 1fr;
    }
  }
</style>
