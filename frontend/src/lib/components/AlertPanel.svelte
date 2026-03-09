<script>
  export let rules = [];
  export let events = [];
  export let onAddRule = () => {};
  export let onRemoveRule = () => {};
  export let onClearEvents = () => {};

  let ruleType = "callsign";
  let ruleQuery = "";

  function submitRule() {
    const normalizedQuery = ruleQuery.trim();
    if (!normalizedQuery) {
      return;
    }

    onAddRule({
      type: ruleType,
      query: normalizedQuery,
    });
    ruleQuery = "";
  }

  function formatEventTime(timestamp) {
    return new Intl.DateTimeFormat("pl-PL", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(timestamp));
  }
</script>

<section class="panel alert-panel">
  <div class="alert-header">
    <div>
      <p class="eyebrow">Alerts</p>
      <h2>Rules and history</h2>
    </div>

    <div class="alert-header-actions">
      <span class="count-pill">{rules.length}</span>
      {#if events.length}
        <button class="clear-button" type="button" on:click={onClearEvents}>Clear log</button>
      {/if}
    </div>
  </div>

  <div class="alert-form">
    <label class="field">
      <span>Match by</span>
      <select bind:value={ruleType}>
        <option value="callsign">Callsign</option>
        <option value="icao24">ICAO24</option>
      </select>
    </label>
    <label class="field">
      <span>Query</span>
      <input
        bind:value={ruleQuery}
        type="text"
        placeholder="LOT, RYR, 48ad08"
        on:keydown={(event) => event.key === "Enter" && submitRule()}
      />
    </label>
    <button class="add-button" type="button" on:click={submitRule}>Add rule</button>
  </div>

  {#if rules.length}
    <div class="rule-list">
      {#each rules as rule}
        <article class="rule-card">
          <div>
            <strong>{rule.query}</strong>
            <p>{rule.type === "callsign" ? "Callsign match" : "ICAO24 match"}</p>
          </div>
          <button class="remove-button" type="button" on:click={() => onRemoveRule(rule.id)}>Remove</button>
        </article>
      {/each}
    </div>
  {:else}
    <p>Add a rule to trigger in-app alerts when matching aircraft appear or disappear.</p>
  {/if}

  {#if events.length}
    <div class="event-list">
      {#each events as event}
        <article class="event-card">
          <div class="event-card-header">
            <strong>{event.message}</strong>
            <span>{formatEventTime(event.timestamp)}</span>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

<style>
  .alert-panel {
    display: grid;
    gap: 0.9rem;
  }

  .alert-header,
  .rule-card,
  .event-card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
  }

  .alert-header-actions {
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

  .alert-form {
    display: grid;
    gap: 0.55rem;
  }

  .field {
    display: grid;
    gap: 0.35rem;
  }

  .field span {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--color-muted);
  }

  .field input,
  .field select,
  .add-button,
  .clear-button,
  .remove-button {
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    padding: 0.78rem 0.9rem;
    font: inherit;
  }

  .field input,
  .field select {
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .add-button,
  .clear-button {
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .remove-button {
    font-weight: 700;
    color: var(--button-danger-text);
    background: var(--button-danger-bg);
    cursor: pointer;
  }

  .rule-list,
  .event-list {
    display: grid;
    gap: 0.6rem;
  }

  .rule-card,
  .event-card {
    padding: 0.9rem;
    border: 1px solid var(--surface-border);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.035);
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

  .event-card-header span {
    font-size: 0.78rem;
    color: var(--color-muted);
    white-space: nowrap;
  }

  @media (max-width: 720px) {
    .alert-header,
    .rule-card,
    .event-card-header {
      display: grid;
    }
  }
</style>
