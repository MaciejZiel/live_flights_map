<section class="panel shortcuts-panel">
  <h2>Keyboard shortcuts</h2>

  <div class="shortcut-list">
    <div><kbd>/</kbd><span>Focus search</span></div>
    <div><kbd>1</kbd><span>Standard map</span></div>
    <div><kbd>2</kbd><span>Satellite map</span></div>
    <div><kbd>3</kbd><span>Dark map</span></div>
    <div><kbd>4</kbd><span>Aviation map</span></div>
    <div><kbd>P</kbd><span>Poland preset</span></div>
    <div><kbd>E</kbd><span>Europe preset</span></div>
    <div><kbd>W</kbd><span>World preset</span></div>
    <div><kbd>F</kbd><span>Follow selected aircraft</span></div>
    <div><kbd>M</kbd><span>Toggle map fullscreen</span></div>
    <div><kbd>0</kbd><span>Reset filters</span></div>
  </div>
</section>

<style>
  .shortcuts-panel {
    display: grid;
    gap: 0.9rem;
  }

  .shortcut-list {
    display: grid;
    gap: 0.65rem;
  }

  .shortcut-list div {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 0.75rem;
  }

  kbd {
    min-width: 2rem;
    padding: 0.3rem 0.45rem;
    border-radius: 8px;
    border: 1px solid rgba(73, 105, 135, 0.18);
    font: inherit;
    font-weight: 800;
    text-align: center;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: inset 0 -2px 0 rgba(18, 57, 93, 0.08);
  }
</style>
