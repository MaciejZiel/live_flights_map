<script>
  import { tick } from "svelte";

  export let query = "";
  export let status = "idle";
  export let error = null;
  export let groups = {};
  export let totalCount = 0;
  export let queryScope = null;
  export let activeResultKey = "";
  export let panelId = "global-search-results";
  export let recentSearches = [];
  export let savedSearches = [];
  export let scopeOptions = [];
  export let onUseSearchQuery = () => {};
  export let onUseSearchScope = () => {};
  export let onSaveSearchQuery = () => {};
  export let onRemoveSavedSearch = () => {};
  export let onQuickAction = () => {};
  export let onSelectResult = () => {};
  export let onHoverResult = () => {};
  export let onRequestSearchFocus = () => {};

  const GROUP_META = {
    aircraft: { label: "Aircraft", glyph: "ACFT" },
    flights: { label: "Flights", glyph: "FLT" },
    registrations: { label: "Registrations", glyph: "REG" },
    airports: { label: "Airports", glyph: "APT" },
    airlines: { label: "Airlines", glyph: "AIR" },
    routes: { label: "Routes", glyph: "RTE" },
    locations: { label: "Locations", glyph: "LOC" },
  };

  function getEntries(value) {
    return Object.entries(value ?? {}).filter(([, items]) => Array.isArray(items) && items.length);
  }

  function getResultLabel(result) {
    return (
      result?.label ??
      result?.callsign ??
      result?.registration ??
      result?.iata ??
      result?.icao ??
      result?.entity_key ??
      "Unknown"
    );
  }

  function getResultSubtitle(result) {
    if (result?.subtitle) {
      return result.subtitle;
    }

    if (result?.entity_type === "aircraft") {
      return [result.callsign, result.operator_code, result.origin_country]
        .filter(Boolean)
        .join(" · ");
    }

    if (result?.entity_type === "flight") {
      return [result.registration ?? result.icao24?.toUpperCase(), result.type_code, result.origin_country]
        .filter(Boolean)
        .join(" · ");
    }

    if (result?.entity_type === "registration") {
      return [result.callsign, result.type_code, result.origin_country]
        .filter(Boolean)
        .join(" · ");
    }

    if (result?.entity_type === "airport") {
      return [result.city, result.country].filter(Boolean).join(", ");
    }

    if (result?.entity_type === "route") {
      return [result.origin_iata ?? result.origin_icao, result.destination_iata ?? result.destination_icao]
        .filter(Boolean)
        .join(" -> ");
    }

    return "Recent traffic intelligence";
  }

  function getMetric(result) {
    if (result?.entity_type === "aircraft") {
      return result.type_code ?? result.icao24?.toUpperCase() ?? "LIVE";
    }

    if (result?.entity_type === "flight") {
      return result.type_code ?? "LIVE";
    }

    if (result?.entity_type === "registration") {
      return result.icao24?.toUpperCase() ?? "OPEN";
    }

    if (result?.entity_type === "airport") {
      return result.iata ?? result.icao ?? result.entity_key;
    }

    if (result?.entity_type === "airline") {
      return `${result.traffic_count ?? 0} flights`;
    }

    if (result?.entity_type === "route") {
      return `${result.route_count ?? 0} tracked`;
    }

    if (result?.entity_type === "location") {
      return `Zoom ${result.zoom ?? "?"}`;
    }

    return result?.entity_key ?? "Open";
  }

  function buildResultKey(result) {
    return `${result?.entity_type ?? "entity"}:${result?.entity_key ?? result?.icao24 ?? result?.label ?? "unknown"}`;
  }

  function buildResultOptionId(resultOrKey) {
    const rawKey =
      typeof resultOrKey === "string" && resultOrKey
        ? resultOrKey
        : buildResultKey(resultOrKey);
    return `search-option-${rawKey.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase()}`;
  }

  function focusResult(result) {
    if (typeof document === "undefined" || !result) {
      return;
    }

    document.getElementById(buildResultOptionId(result))?.focus();
  }

  function getQuickActions(result) {
    if (result?.entity_type === "flight" || result?.entity_type === "aircraft" || result?.entity_type === "registration") {
      return [
        { id: "open", label: "Open" },
        { id: "track", label: "Track" },
      ];
    }

    if (result?.entity_type === "airport") {
      return [
        { id: "open", label: "Open" },
        { id: "alert", label: "Alert" },
      ];
    }

    if (result?.entity_type === "airline" || result?.entity_type === "route") {
      return [
        { id: "filter", label: "Filter" },
        { id: "alert", label: "Alert" },
      ];
    }

    return [
      { id: "open", label: "Open" },
      { id: "alert", label: "Alert" },
    ];
  }

  function handleQuickAction(event, action, result) {
    event.preventDefault();
    event.stopPropagation();
    onQuickAction(action, result);
  }

  function handleResultKeydown(event, result) {
    const currentIndex = allResults.findIndex((entry) => buildResultKey(entry) === buildResultKey(result));
    if (currentIndex < 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      const nextResult = allResults[(currentIndex + 1) % allResults.length];
      onHoverResult(nextResult);
      focusResult(nextResult);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      const nextResult = allResults[(currentIndex - 1 + allResults.length) % allResults.length];
      onHoverResult(nextResult);
      focusResult(nextResult);
      return;
    }

    if (event.key === "Home") {
      event.preventDefault();
      onHoverResult(allResults[0]);
      focusResult(allResults[0]);
      return;
    }

    if (event.key === "End") {
      event.preventDefault();
      const lastResult = allResults[allResults.length - 1];
      onHoverResult(lastResult);
      focusResult(lastResult);
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      onRequestSearchFocus();
    }
  }

  $: groupEntries = getEntries(groups);
  $: allResults = groupEntries.flatMap(([, items]) => items);
  $: if (activeResultKey) {
    void tick().then(() => {
      if (typeof document === "undefined") {
        return;
      }

      document
        .getElementById(buildResultOptionId(activeResultKey))
        ?.scrollIntoView({ block: "nearest" });
    });
  }
</script>

<section class="search-panel" aria-label="Entity search results">
  {#if status === "loading"}
    <p class="search-copy">Searching aircraft, flights, airports, airlines, routes and locations…</p>
  {:else if error}
    <p class="search-copy search-copy-error">{error}</p>
  {:else if groupEntries.length}
    <div class="search-summary">
      <div>
        <strong>{totalCount}</strong>
        <span>{query.trim() ? `results for "${query.trim()}"` : "results"}</span>
      </div>
      <div class="search-summary-actions">
        {#if queryScope}
          <span class="search-scope-pill">{queryScope}</span>
        {/if}
        <button class="search-summary-button" type="button" on:click={onSaveSearchQuery}>
          Save search
        </button>
        <small>Use ↑ ↓ to navigate, Enter to open, Esc to return</small>
      </div>
    </div>

    <div class="search-groups" id={panelId} role="listbox" aria-label={`Search results for ${query.trim() || "current query"}`}>
      {#each groupEntries as [groupName, items]}
      <section class="search-group" role="group" aria-label={GROUP_META[groupName]?.label ?? groupName}>
        <div class="search-group-header">
          <span>{GROUP_META[groupName]?.label ?? groupName}</span>
          <strong>{items.length}</strong>
        </div>

        <div class="search-result-list">
          {#each items as result}
            <article
              class:active={activeResultKey === buildResultKey(result)}
              class="search-row"
            >
              <button
                class="search-row-hitbox"
                type="button"
                id={buildResultOptionId(result)}
                role="option"
                aria-current={activeResultKey === buildResultKey(result) ? "true" : undefined}
                aria-selected={activeResultKey === buildResultKey(result)}
                on:mouseenter={() => onHoverResult(result)}
                on:focus={() => onHoverResult(result)}
                on:keydown={(event) => handleResultKeydown(event, result)}
                on:click={() => onSelectResult(result)}
              >
                <span class="search-row-glyph">{GROUP_META[groupName]?.glyph ?? "..."}</span>
                <span class="search-row-main">
                  <strong>{getResultLabel(result)}</strong>
                  <small>{getResultSubtitle(result) || "No metadata yet"}</small>
                </span>
                <span class="search-row-meta">
                  <strong>{getMetric(result)}</strong>
                </span>
              </button>
              <span class="search-row-actions">
                {#each getQuickActions(result) as action}
                  <button
                    class="search-action"
                    type="button"
                    on:click={(event) => handleQuickAction(event, action.id, result)}
                  >
                    {action.label}
                  </button>
                {/each}
              </span>
            </article>
          {/each}
        </div>
      </section>
      {/each}
    </div>
  {:else if query.trim().length >= 2}
    <div class="search-empty-state">
      <p class="search-copy">No live aircraft, flights or airport entities matched this search yet.</p>
      <div class="search-scope-list">
        {#each scopeOptions as scope}
          <button class="search-scope-button" type="button" on:click={() => onUseSearchScope(scope.prefix)}>
            {scope.label}
          </button>
        {/each}
      </div>
    </div>
  {:else if queryScope}
    <div class="search-start-panel">
      <p class="search-copy">Finish the scoped search by adding a value after <strong>{queryScope}:</strong>.</p>
      <div class="search-scope-list">
        {#each scopeOptions as scope}
          <button class="search-scope-button" type="button" on:click={() => onUseSearchScope(scope.prefix)}>
            {scope.example}
          </button>
        {/each}
      </div>
    </div>
  {:else}
    <div class="search-start-panel">
      <p class="search-copy">Type at least two characters to search aircraft, flights, airports, airlines, routes and saved locations.</p>

      <section class="search-helper-block">
        <div class="search-helper-header">
          <strong>Scope search</strong>
          <small>Use prefixes to jump faster</small>
        </div>
        <div class="search-scope-list">
          {#each scopeOptions as scope}
            <button class="search-scope-button" type="button" on:click={() => onUseSearchScope(scope.prefix)}>
              {scope.prefix}
              <span>{scope.label}</span>
            </button>
          {/each}
        </div>
      </section>

      {#if savedSearches.length}
        <section class="search-helper-block">
          <div class="search-helper-header">
            <strong>Saved searches</strong>
            <small>One click to reopen</small>
          </div>
          <div class="search-chip-list">
            {#each savedSearches as savedQuery}
              <div class="search-chip-shell">
                <button class="search-chip" type="button" on:click={() => onUseSearchQuery(savedQuery)}>
                  {savedQuery}
                </button>
                <button
                  class="search-chip-remove"
                  type="button"
                  aria-label={`Remove saved search ${savedQuery}`}
                  on:click={() => onRemoveSavedSearch(savedQuery)}
                >
                  ×
                </button>
              </div>
            {/each}
          </div>
        </section>
      {/if}

      {#if recentSearches.length}
        <section class="search-helper-block">
          <div class="search-helper-header">
            <strong>Recent searches</strong>
            <small>Recent lookup memory</small>
          </div>
          <div class="search-chip-list">
            {#each recentSearches as recentQuery}
              <button class="search-chip" type="button" on:click={() => onUseSearchQuery(recentQuery)}>
                {recentQuery}
              </button>
            {/each}
          </div>
        </section>
      {/if}
    </div>
  {/if}
</section>

<style>
  .search-panel {
    display: grid;
    gap: 0.7rem;
  }

  .search-summary {
    display: flex;
    justify-content: space-between;
    gap: 0.9rem;
    align-items: end;
    padding: 0 0.25rem;
  }

  .search-summary-actions {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .search-summary div {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
  }

  .search-summary strong {
    font-size: 1rem;
    color: #f5f7fb;
  }

  .search-summary span,
  .search-summary small,
  .search-copy {
    font-size: 0.76rem;
    color: rgba(199, 209, 220, 0.78);
  }

  .search-summary-button,
  .search-scope-button,
  .search-action,
  .search-chip,
  .search-chip-remove {
    font: inherit;
    cursor: pointer;
  }

  .search-summary-button,
  .search-scope-pill,
  .search-chip,
  .search-chip-remove,
  .search-action {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.05);
  }

  .search-summary-button {
    padding: 0.38rem 0.62rem;
    font-size: 0.7rem;
    font-weight: 800;
    color: #eef3f8;
  }

  .search-scope-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 1.8rem;
    padding: 0 0.58rem;
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .search-copy {
    margin: 0;
    padding: 0.15rem 0.25rem;
    line-height: 1.5;
  }

  .search-copy-error {
    color: #ffd5d5;
  }

  .search-group {
    display: grid;
    gap: 0.45rem;
  }

  .search-groups {
    display: grid;
    gap: 0.7rem;
  }

  .search-group-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
    padding: 0 0.25rem;
  }

  .search-group-header span {
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(182, 193, 205, 0.68);
  }

  .search-group-header strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.9rem;
    min-height: 1.7rem;
    padding: 0 0.45rem;
    border-radius: 999px;
    font-size: 0.7rem;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.08);
  }

  .search-result-list {
    display: grid;
    gap: 0.36rem;
  }

  .search-row {
    display: grid;
    gap: 0.38rem;
  }

  .search-row-hitbox {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.6rem;
    align-items: center;
    width: 100%;
    padding: 0.78rem 0.82rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    font: inherit;
    color: inherit;
    background: linear-gradient(180deg, rgba(32, 35, 41, 0.98) 0%, rgba(19, 22, 26, 0.98) 100%);
    text-align: left;
    cursor: pointer;
    transition:
      transform 160ms ease,
      border-color 160ms ease,
      background 160ms ease;
  }

  .search-row-hitbox:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.24);
    background: linear-gradient(180deg, rgba(44, 37, 18, 0.98) 0%, rgba(23, 22, 17, 0.98) 100%);
  }

  .search-row-hitbox:focus-visible {
    outline: none;
    border-color: rgba(120, 200, 255, 0.4);
    background: linear-gradient(180deg, rgba(18, 43, 63, 0.98) 0%, rgba(13, 26, 39, 0.98) 100%);
    box-shadow:
      0 0 0 1px rgba(120, 200, 255, 0.18),
      0 0 0 4px rgba(120, 200, 255, 0.16);
  }

  .search-row.active .search-row-hitbox {
    border-color: rgba(120, 200, 255, 0.34);
    background: linear-gradient(180deg, rgba(14, 36, 54, 0.98) 0%, rgba(12, 22, 33, 0.98) 100%);
    box-shadow: 0 0 0 1px rgba(120, 200, 255, 0.16);
  }

  .search-row-glyph {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.15rem;
    min-height: 2.15rem;
    border-radius: 12px;
    font-size: 0.62rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .search-row-main {
    display: grid;
    gap: 0.16rem;
    min-width: 0;
  }

  .search-row-main strong {
    color: #f5f7fb;
    font-size: 0.84rem;
  }

  .search-row-main small {
    color: rgba(193, 202, 214, 0.72);
    font-size: 0.73rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .search-row-meta {
    justify-self: end;
  }

  .search-row-meta strong {
    padding: 0.24rem 0.5rem;
    border-radius: 999px;
    font-size: 0.67rem;
    font-weight: 800;
    color: #dfe6ef;
    background: rgba(255, 255, 255, 0.08);
    white-space: nowrap;
  }

  .search-row-actions {
    display: flex;
    gap: 0.28rem;
    flex-wrap: wrap;
    justify-content: flex-end;
    padding: 0 0.2rem;
  }

  .search-action {
    padding: 0.28rem 0.5rem;
    font-size: 0.64rem;
    font-weight: 800;
    color: rgba(228, 235, 243, 0.88);
  }

  .search-start-panel,
  .search-empty-state,
  .search-helper-block {
    display: grid;
    gap: 0.62rem;
  }

  .search-helper-block {
    padding: 0.72rem 0.76rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.025);
  }

  .search-helper-header {
    display: flex;
    justify-content: space-between;
    gap: 0.55rem;
    align-items: baseline;
  }

  .search-helper-header strong {
    color: #f4f7fb;
    font-size: 0.8rem;
  }

  .search-helper-header small {
    color: rgba(193, 202, 214, 0.68);
    font-size: 0.68rem;
  }

  .search-scope-list,
  .search-chip-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.42rem;
  }

  .search-scope-button,
  .search-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.66rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 800;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .search-scope-button span {
    color: rgba(199, 209, 220, 0.7);
    font-size: 0.66rem;
    font-weight: 700;
  }

  .search-chip-shell {
    display: inline-flex;
    align-items: center;
    gap: 0.22rem;
  }

  .search-chip-remove {
    width: 1.8rem;
    height: 1.8rem;
    color: rgba(238, 243, 248, 0.86);
  }

  @media (max-width: 720px) {
    .search-summary,
    .search-helper-header {
      display: grid;
    }

    .search-row {
      gap: 0.32rem;
    }

    .search-row-hitbox {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .search-row-meta {
      grid-column: 1 / -1;
      justify-self: start;
    }

    .search-row-actions {
      justify-content: flex-start;
    }
  }
</style>
