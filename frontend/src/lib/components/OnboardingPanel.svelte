<script>
  export let onDismiss = () => {};
</script>

<section class="panel onboarding-panel">
  <div class="onboarding-header">
    <div>
      <p class="eyebrow">Quick start</p>
      <h2>How to read this radar</h2>
    </div>
    <button class="dismiss-button" type="button" on:click={onDismiss} title="Hide onboarding tips">
      Hide tips
    </button>
  </div>

  <ul>
    <li>Click any aircraft marker to inspect details and optionally keep it centered.</li>
    <li>Use <kbd>/</kbd> to jump to search, then filter live traffic by altitude and freshness.</li>
    <li>Press <kbd>P</kbd>, <kbd>E</kbd>, or <kbd>W</kbd> to jump between Poland, Europe, and world views.</li>
    <li>Press <kbd>M</kbd> for fullscreen radar and <kbd>F</kbd> to follow the selected aircraft.</li>
  </ul>
</section>

<style>
  .onboarding-panel {
    display: grid;
    gap: 0.9rem;
    border: 1px solid var(--surface-border);
  }

  .onboarding-header {
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

  h2 {
    margin: 0;
    font-size: 1rem;
  }

  .dismiss-button {
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

  ul {
    display: grid;
    gap: 0.65rem;
    margin: 0;
    padding-left: 1.1rem;
  }

  li {
    line-height: 1.45;
  }

  kbd {
    border: 1px solid var(--kbd-border);
    border-radius: 8px;
    padding: 0.1rem 0.38rem;
    font-size: 0.78rem;
    font-weight: 700;
    background: var(--kbd-bg);
  }

  @media (max-width: 720px) {
    .onboarding-header {
      display: grid;
    }
  }
</style>
