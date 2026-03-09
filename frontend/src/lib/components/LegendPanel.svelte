<section class="panel legend-panel">
  <h2>Legend</h2>

  <div class="legend-list">
    <div class="legend-item">
      <span class="legend-marker aircraft-default"></span>
      <span>Tracked aircraft</span>
    </div>
    <div class="legend-item">
      <span class="legend-marker aircraft-selected"></span>
      <span>Selected aircraft</span>
    </div>
    <div class="legend-item">
      <span class="legend-marker aircraft-cluster">12</span>
      <span>Clustered traffic</span>
    </div>
    <div class="legend-item">
      <span class="legend-pill live">Live</span>
      <span>Fresh upstream snapshot</span>
    </div>
    <div class="legend-item">
      <span class="legend-pill cached">Cached</span>
      <span>Fallback snapshot while upstream cools down</span>
    </div>
  </div>
</section>

<style>
  .legend-panel {
    display: grid;
    gap: 0.9rem;
  }

  .legend-list {
    display: grid;
    gap: 0.85rem;
  }

  .legend-item {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 0.75rem;
    line-height: 1.35;
  }

  .legend-marker {
    display: grid;
    place-items: center;
    width: 2.2rem;
    height: 2.2rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 800;
    color: #f6fbff;
  }

  .aircraft-default {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .aircraft-selected {
    background: linear-gradient(180deg, #78c8ff 0%, #45a7ee 100%);
  }

  .aircraft-cluster {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    box-shadow: inset 0 0 0 4px rgba(0, 0, 0, 0.12);
  }

  .legend-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 4.7rem;
    padding: 0.45rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
  }

  .legend-pill.live {
    color: var(--status-online-text);
    background: var(--status-online-bg);
  }

  .legend-pill.cached {
    color: var(--banner-warning-text);
    background: var(--banner-warning-bg);
  }
</style>
