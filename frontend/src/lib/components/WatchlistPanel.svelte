<script>
  export let entries = [];
  export let selectedIcao24 = null;
  export let watchModeEnabled = false;
  export let onToggleWatchMode = () => {};
  export let onSelectFlight = () => {};
  export let onRemoveFlight = () => {};
</script>

<section class="panel watchlist-panel">
  <div class="watchlist-header">
    <div>
      <p class="eyebrow">Local workspace</p>
      <h2>Saved aircraft</h2>
    </div>

    <div class="watchlist-header-actions">
      <span class="count-pill">{entries.length}</span>
      <button class:active={watchModeEnabled} class="watch-mode-button" type="button" on:click={onToggleWatchMode}>
        {#if watchModeEnabled}
          Highlight saved
        {:else}
          Show all equally
        {/if}
      </button>
    </div>
  </div>

  {#if entries.length}
    <div class="watchlist-list">
      {#each entries as entry}
        <article class:selected={entry.icao24 === selectedIcao24} class="watch-card">
          <div class="watch-card-header">
            <strong>{entry.flight?.callsign ?? entry.icao24}</strong>
            <span class:live={entry.isLive}>{entry.isLive ? "Live" : "Offline"}</span>
          </div>
          <p>{entry.flight?.origin_country ?? "Last seen aircraft"}</p>
          <div class="watch-card-actions">
            <button class="watch-action" type="button" on:click={() => onSelectFlight(entry.icao24)}>
              Open
            </button>
            <button class="watch-remove" type="button" on:click={() => onRemoveFlight(entry.icao24)}>
              Remove
            </button>
          </div>
        </article>
      {/each}
    </div>
  {:else}
    <p>Add an aircraft in Local workspace to keep it saved on this device.</p>
  {/if}
</section>

<style>
  .watchlist-panel {
    display: grid;
    gap: 0.9rem;
  }

  .watchlist-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .watchlist-header-actions {
    display: flex;
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

  .watch-mode-button,
  .watch-action,
  .watch-remove {
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    padding: 0.76rem 0.88rem;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .watch-mode-button,
  .watch-action {
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
  }

  .watch-mode-button.active {
    border: 0;
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
  }

  .watch-remove {
    color: var(--button-danger-text);
    background: var(--button-danger-bg);
  }

  .watchlist-list {
    display: grid;
    gap: 0.65rem;
  }

  .watch-card {
    display: grid;
    gap: 0.6rem;
    padding: 0.9rem;
    border: 1px solid var(--surface-border);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.035);
  }

  .watch-card.selected {
    box-shadow: inset 0 0 0 2px rgba(75, 183, 245, 0.35);
  }

  .watch-card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .watch-card-header span {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--color-muted);
  }

  .watch-card-header span.live {
    color: var(--status-online-text);
  }

  .watch-card-actions {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
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
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.08);
  }

  @media (max-width: 720px) {
    .watchlist-header {
      display: grid;
    }
  }
</style>
