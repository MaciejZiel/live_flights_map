<script>
  export let views = [];
  export let activeViewId = null;
  export let currentName = "";
  export let onNameChange = () => {};
  export let onSaveView = () => {};
  export let onLoadView = () => {};
  export let onDeleteView = () => {};
</script>

<section class="panel saved-views-panel">
  <div>
    <p class="eyebrow">Workspace</p>
    <h2>Saved views</h2>
  </div>

  <div class="save-row">
    <input
      type="text"
      placeholder="Warsaw arrivals, Cargo sweep..."
      value={currentName}
      on:input={(event) => onNameChange(event.currentTarget.value)}
      on:keydown={(event) => event.key === "Enter" && onSaveView()}
    />
    <button class="save-button" type="button" on:click={onSaveView}>Save view</button>
  </div>

  {#if views.length}
    <div class="view-list">
      {#each views as view}
        <article class:active={view.id === activeViewId} class="view-card">
          <div>
            <strong>{view.name}</strong>
            <p>{view.watchlistCount} watched · {view.mapStyle} map</p>
          </div>
          <div class="view-actions">
            <button class="view-load" type="button" on:click={() => onLoadView(view.id)}>
              {view.id === activeViewId ? "Loaded" : "Load"}
            </button>
            <button class="view-delete" type="button" on:click={() => onDeleteView(view.id)}>
              Delete
            </button>
          </div>
        </article>
      {/each}
    </div>
  {:else}
    <p>Save a workspace to restore a complete radar setup later.</p>
  {/if}
</section>

<style>
  .saved-views-panel {
    display: grid;
    gap: 0.9rem;
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

  .save-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.55rem;
  }

  .save-row input,
  .save-button,
  .view-load,
  .view-delete {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
  }

  .save-row input {
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .save-button,
  .view-load {
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .view-delete {
    font-weight: 700;
    color: var(--button-danger-text);
    background: var(--button-danger-bg);
    cursor: pointer;
  }

  .view-list {
    display: grid;
    gap: 0.65rem;
  }

  .view-card {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    padding: 0.85rem;
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.04);
  }

  .view-card.active {
    box-shadow: inset 0 0 0 2px rgba(75, 183, 245, 0.35);
  }

  .view-actions {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
  }

  @media (max-width: 720px) {
    .save-row,
    .view-card {
      grid-template-columns: 1fr;
      display: grid;
    }
  }
</style>
