<script>
  export let snapshots = [];
  export let activeSnapshot = null;
  export let activeIndex = -1;
  export let isPlaying = false;
  export let anchorTimestamp = null;
  export let windowMinutes = 90;
  export let playbackSpeed = 1;
  export let canStepBackward = false;
  export let canStepForward = false;
  export let onSelectIndex = () => {};
  export let onReturnToLive = () => {};
  export let onJumpStart = () => {};
  export let onJumpLatest = () => {};
  export let onSetAnchorTimestamp = () => {};
  export let onClearAnchorTimestamp = () => {};
  export let onSetWindowMinutes = () => {};
  export let onSetPlaybackSpeed = () => {};
  export let onStepBackward = () => {};
  export let onStepForward = () => {};
  export let onTogglePlayback = () => {};
  export let compareSnapshot = null;
  export let compareSummary = null;
  export let onMarkCompare = () => {};
  export let onClearCompare = () => {};
  export let onJumpRelative = () => {};
  export let onJumpToTimestamp = () => {};

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

  function formatRangeLabel(value) {
    return value < 60 ? `${value}m` : `${Math.round(value / 60)}h`;
  }

  function formatDateTimeInputValue(value) {
    if (!value) {
      return "";
    }

    const timestamp = new Date(value);
    if (Number.isNaN(timestamp.getTime())) {
      return "";
    }

    const timezoneOffset = timestamp.getTimezoneOffset() * 60000;
    return new Date(timestamp.getTime() - timezoneOffset).toISOString().slice(0, 16);
  }

  function handleAnchorChange(event) {
    onSetAnchorTimestamp(event.currentTarget.value);
  }

  function handleJumpChange(event) {
    onJumpToTimestamp(event.currentTarget.value);
  }

  $: sliderValue = activeIndex >= 0 ? activeIndex : Math.max(0, snapshots.length - 1);
  $: activeSnapshotLabel = snapshots[sliderValue] ? formatSnapshotTime(snapshots[sliderValue].fetchedAt) : "--:--";
  $: firstSnapshotLabel = snapshots[0] ? formatSnapshotTime(snapshots[0].fetchedAt) : "--:--";
  $: lastSnapshotLabel = snapshots[snapshots.length - 1]
    ? formatSnapshotTime(snapshots[snapshots.length - 1].fetchedAt)
    : "--:--";
  $: anchorInputValue = formatDateTimeInputValue(anchorTimestamp);
  $: jumpInputValue = formatDateTimeInputValue(
    activeSnapshot?.fetchedAt ?? snapshots[sliderValue]?.fetchedAt ?? snapshots[snapshots.length - 1]?.fetchedAt
  );
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

  <div class="timeline-anchor-row">
    <span>{anchorTimestamp ? "Replay end" : "Following live tail"}</span>
    <div class="timeline-anchor-controls">
      <input type="datetime-local" value={anchorInputValue} on:change={handleAnchorChange} />
      <button class="live-button" type="button" on:click={onClearAnchorTimestamp}>
        Live tail
      </button>
    </div>
  </div>

  {#if snapshots.length < 2}
    <p>Collecting snapshots. Replay becomes available after the second update.</p>
  {:else}
    <div class="timeline-range-row">
      <span>Archive range</span>
      <div class="range-chip-row">
        {#each [30, 90, 180] as option}
          <button
            class:active={windowMinutes === option}
            class="range-chip"
            type="button"
            on:click={() => onSetWindowMinutes(option)}
          >
            {formatRangeLabel(option)}
          </button>
        {/each}
      </div>
    </div>

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

    <div class="timeline-range-summary">
      <span>{firstSnapshotLabel}</span>
      <strong>{snapshots.length} snapshots in archive</strong>
      <span>{lastSnapshotLabel}</span>
    </div>

    <div class="timeline-jump-row">
      <span>Jump in time</span>
      <div class="timeline-anchor-controls">
        <button class="range-chip" type="button" on:click={() => onJumpRelative(-60)}>-60m</button>
        <button class="range-chip" type="button" on:click={() => onJumpRelative(-30)}>-30m</button>
        <button class="range-chip" type="button" on:click={() => onJumpRelative(-15)}>-15m</button>
        <input type="datetime-local" value={jumpInputValue} on:change={handleJumpChange} />
        <button class="range-chip" type="button" on:click={() => onJumpRelative(15)}>+15m</button>
        <button class="range-chip" type="button" on:click={() => onJumpRelative(30)}>+30m</button>
      </div>
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

    <div class="timeline-compare-row">
      <span>{compareSnapshot ? "Compare baseline set" : "Compare snapshots"}</span>
      <div class="range-chip-row">
        <button class="range-chip" type="button" on:click={onMarkCompare}>
          {compareSnapshot ? "Replace baseline" : "Mark baseline"}
        </button>
        {#if compareSnapshot}
          <button class="range-chip" type="button" on:click={onClearCompare}>Clear</button>
        {/if}
      </div>
    </div>

    {#if compareSummary}
      <div class="timeline-compare-summary-grid">
        <article>
          <span>Baseline</span>
          <strong>{formatSnapshotTime(compareSummary.baseLabel)}</strong>
          <small>{compareSummary.baseCount} aircraft</small>
        </article>
        <article>
          <span>Current</span>
          <strong>{formatSnapshotTime(compareSummary.activeLabel)}</strong>
          <small>{compareSummary.activeCount} aircraft</small>
        </article>
        <article>
          <span>Stayed</span>
          <strong>{compareSummary.persisted}</strong>
          <small>visible in both</small>
        </article>
        <article>
          <span>New</span>
          <strong>{compareSummary.arrivals}</strong>
          <small>appeared later</small>
        </article>
        <article>
          <span>Gone</span>
          <strong>{compareSummary.departures}</strong>
          <small>left the view</small>
        </article>
        <article>
          <span>Net change</span>
          <strong>{compareSummary.trafficDelta > 0 ? `+${compareSummary.trafficDelta}` : compareSummary.trafficDelta}</strong>
          <small>traffic delta</small>
        </article>
      </div>
    {/if}
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

  .timeline-range-row,
  .timeline-range-summary,
  .timeline-anchor-row,
  .timeline-speed-row,
  .timeline-jump-row,
  .timeline-compare-row {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .timeline-range-row span,
  .timeline-range-summary span,
  .timeline-anchor-row span,
  .timeline-speed-row span,
  .timeline-jump-row span,
  .timeline-compare-row span {
    font-size: 0.8rem;
    color: var(--color-muted);
  }

  .timeline-anchor-controls {
    display: inline-flex;
    gap: 0.45rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .timeline-range-summary strong {
    font-size: 0.78rem;
    color: var(--color-text);
  }

  .range-chip-row {
    display: inline-flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .range-chip {
    border: 1px solid var(--surface-border);
    border-radius: 999px;
    padding: 0.42rem 0.68rem;
    font: inherit;
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .range-chip.active {
    color: #f4f7fb;
    background: rgba(120, 200, 255, 0.16);
    border-color: rgba(120, 200, 255, 0.22);
  }

  .timeline-speed-row select {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.56rem 0.72rem;
    font: inherit;
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .timeline-anchor-controls input {
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

  .timeline-compare-summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .timeline-compare-summary-grid article {
    display: grid;
    gap: 0.14rem;
    padding: 0.72rem 0.78rem;
    border-radius: 14px;
    border: 1px solid var(--surface-border);
    background: rgba(255, 255, 255, 0.03);
  }

  .timeline-compare-summary-grid span,
  .timeline-compare-summary-grid small {
    color: var(--color-muted);
    font-size: 0.75rem;
  }

  .timeline-compare-summary-grid strong {
    color: var(--color-text);
    font-size: 0.94rem;
  }

  @media (max-width: 720px) {
    .replay-header,
    .timeline-meta,
    .timeline-range-row,
    .timeline-range-summary,
    .timeline-anchor-row,
    .timeline-speed-row,
    .timeline-jump-row,
    .timeline-compare-row {
      display: grid;
    }

    .timeline-controls {
      grid-template-columns: 1fr;
    }

    .timeline-compare-summary-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
