<script>
  import {
    ALERT_RULE_OPTIONS,
    ALERT_SEVERITY_OPTIONS,
    getAlertRuleDefaultSeverity,
    getAlertRuleLabel,
    getAlertRuleOption,
    getAlertSeverityLabel,
  } from "../utils/alertRules.js";

  export let rules = [];
  export let events = [];
  export let onAddRule = () => {};
  export let onRemoveRule = () => {};
  export let onClearEvents = () => {};
  export let deliverySettings = {};
  export let onUpdateDeliverySettings = () => {};
  export let onEnableBrowserNotifications = () => {};

  let ruleType = "callsign";
  let ruleQuery = "";
  let ruleSeverity = "important";
  let ruleCooldownMinutes = 10;

  function submitRule() {
    const option = getAlertRuleOption(ruleType);
    const normalizedQuery = ruleQuery.trim();
    if (!normalizedQuery && !option?.queryOptional) {
      return;
    }

    onAddRule({
      type: ruleType,
      query: option?.queryOptional ? option?.placeholder || "" : normalizedQuery,
      severity: ruleSeverity,
      cooldownMinutes: ruleCooldownMinutes,
    });
    if (!option?.queryOptional) {
      ruleQuery = "";
    }
  }

  function formatEventTime(timestamp) {
    return new Intl.DateTimeFormat("pl-PL", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(timestamp));
  }

  $: if (getAlertRuleOption(ruleType)) {
    ruleSeverity = getAlertRuleDefaultSeverity(ruleType);
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
        {#each ALERT_RULE_OPTIONS as option}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>
    </label>
    <label class="field">
      <span>Query</span>
      <input
        bind:value={ruleQuery}
        type="text"
        placeholder={getAlertRuleOption(ruleType)?.placeholder ?? "LOT, SP-LVQ, B38M, Poland, 48ad08"}
        disabled={Boolean(getAlertRuleOption(ruleType)?.queryOptional)}
        on:keydown={(event) => event.key === "Enter" && submitRule()}
      />
    </label>
    <label class="field">
      <span>Severity</span>
      <select bind:value={ruleSeverity}>
        {#each ALERT_SEVERITY_OPTIONS as option}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>
    </label>
    <label class="field">
      <span>Cooldown</span>
      <select bind:value={ruleCooldownMinutes}>
        {#each [5, 10, 15, 30, 60] as minutes}
          <option value={minutes}>{minutes} minutes</option>
        {/each}
      </select>
    </label>
    <button class="add-button" type="button" on:click={submitRule}>Add rule</button>
  </div>

  <section class="delivery-card">
    <div class="event-card-header">
      <strong>Delivery</strong>
      {#if deliverySettings.browserPermission}
        <span>{deliverySettings.browserPermission}</span>
      {/if}
    </div>
    <div class="delivery-grid">
      <label class="delivery-toggle">
        <input
          type="checkbox"
          checked={Boolean(deliverySettings.browserNotificationsEnabled)}
          on:change={(event) => {
            onUpdateDeliverySettings({
              browserNotificationsEnabled: event.currentTarget.checked,
            });
            if (event.currentTarget.checked) {
              onEnableBrowserNotifications();
            }
          }}
        />
        <span>Browser notifications</span>
      </label>
      <label class="delivery-toggle">
        <input
          type="checkbox"
          checked={Boolean(deliverySettings.webhookEnabled)}
          on:change={(event) =>
            onUpdateDeliverySettings({
              webhookEnabled: event.currentTarget.checked,
            })}
        />
        <span>Webhook</span>
      </label>
      <label class="field field-wide">
        <span>Webhook URL</span>
        <input
          type="url"
          value={deliverySettings.webhookUrl ?? ""}
          placeholder="https://example.com/alerts"
          on:change={(event) =>
            onUpdateDeliverySettings({
              webhookUrl: event.currentTarget.value,
            })}
        />
      </label>
      <label class="delivery-toggle">
        <input
          type="checkbox"
          checked={Boolean(deliverySettings.suppressInfo)}
          on:change={(event) =>
            onUpdateDeliverySettings({
              suppressInfo: event.currentTarget.checked,
            })}
        />
        <span>Mute info alerts</span>
      </label>
    </div>
  </section>

  {#if rules.length}
    <div class="rule-list">
      {#each rules as rule}
        <article class="rule-card">
          <div>
            <strong>{rule.query}</strong>
            <p>{getAlertRuleLabel(rule.type)} · {getAlertSeverityLabel(rule.severity)} · {rule.cooldownMinutes ?? 10}m cooldown</p>
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
          <div class="event-meta-row">
            <span class={`severity-pill severity-${event.severity ?? "info"}`}>{getAlertSeverityLabel(event.severity ?? "info")}</span>
            {#if event.delivery?.webhook}
              <small>Webhook {event.delivery.webhook}</small>
            {/if}
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

  .delivery-card {
    display: grid;
    gap: 0.7rem;
    padding: 0.9rem;
    border: 1px solid var(--surface-border);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.028);
  }

  .delivery-grid {
    display: grid;
    gap: 0.65rem;
  }

  .delivery-toggle {
    display: flex;
    gap: 0.6rem;
    align-items: center;
    color: var(--color-text);
  }

  .field-wide {
    grid-column: 1 / -1;
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

  .event-meta-row {
    display: flex;
    gap: 0.55rem;
    align-items: center;
    margin-top: 0.5rem;
  }

  .severity-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.22rem 0.55rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .severity-info {
    color: #d7ecff;
    background: rgba(74, 136, 214, 0.18);
  }

  .severity-important {
    color: #ffe7b2;
    background: rgba(184, 121, 19, 0.2);
  }

  .severity-critical {
    color: #ffd9d9;
    background: rgba(166, 48, 48, 0.24);
  }

  .event-meta-row small {
    color: var(--color-muted);
    font-size: 0.74rem;
  }

  @media (max-width: 720px) {
    .alert-header,
    .rule-card,
    .event-card-header {
      display: grid;
    }
  }
</style>
