<script>
  export let sessions = [];
  export let activeSessionId = null;
  export let onSaveSession = () => {};
  export let onLoadSession = () => {};
  export let onDeleteSession = () => {};
</script>

<section class="panel session-panel">
  <div class="session-header">
    <div>
      <p class="eyebrow">Session library</p>
      <h2>Saved monitoring sessions</h2>
    </div>

    <button class="session-save" type="button" on:click={onSaveSession}>Save current session</button>
  </div>

  {#if sessions.length}
    <div class="session-list">
      {#each sessions as session}
        <article class:active={session.id === activeSessionId} class="session-card">
          <div>
            <strong>{session.label}</strong>
            <p>{session.snapshots.length} snapshots</p>
          </div>
          <div class="session-actions">
            <button class="session-load" type="button" on:click={() => onLoadSession(session.id)}>
              {session.id === activeSessionId ? "Loaded" : "Load"}
            </button>
            <button class="session-delete" type="button" on:click={() => onDeleteSession(session.id)}>
              Delete
            </button>
          </div>
        </article>
      {/each}
    </div>
  {:else}
    <p>Save a live monitoring session to replay it later.</p>
  {/if}
</section>

<style>
  .session-panel {
    display: grid;
    gap: 0.9rem;
  }

  .session-header,
  .session-card,
  .session-actions {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
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

  .session-list {
    display: grid;
    gap: 0.65rem;
  }

  .session-card {
    padding: 0.85rem;
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.04);
  }

  .session-card.active {
    box-shadow: inset 0 0 0 2px rgba(75, 183, 245, 0.35);
  }

  .session-save,
  .session-load,
  .session-delete {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.72rem 0.82rem;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .session-save,
  .session-load {
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
  }

  .session-delete {
    color: var(--button-danger-text);
    background: var(--button-danger-bg);
  }

  @media (max-width: 720px) {
    .session-header,
    .session-card,
    .session-actions {
      display: grid;
    }
  }
</style>
