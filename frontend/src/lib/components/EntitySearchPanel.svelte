<script>
  export let query = "";
  export let status = "idle";
  export let error = null;
  export let groups = {};
  export let totalCount = 0;
  export let activeResultKey = "";
  export let onSelectResult = () => {};
  export let onHoverResult = () => {};

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

  $: groupEntries = getEntries(groups);
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
      <small>Use ↑ ↓ to navigate, Enter to open</small>
    </div>

    {#each groupEntries as [groupName, items]}
      <section class="search-group">
        <div class="search-group-header">
          <span>{GROUP_META[groupName]?.label ?? groupName}</span>
          <strong>{items.length}</strong>
        </div>

        <div class="search-result-list">
          {#each items as result}
            <button
              class:active={activeResultKey === buildResultKey(result)}
              class="search-row"
              type="button"
              aria-current={activeResultKey === buildResultKey(result) ? "true" : undefined}
              on:mouseenter={() => onHoverResult(result)}
              on:focus={() => onHoverResult(result)}
              on:click={() => onSelectResult(result)}
            >
              <span class="search-row-glyph">{GROUP_META[groupName]?.glyph ?? "..."}</span>
              <span class="search-row-main">
                <strong>{getResultLabel(result)}</strong>
                <small>{getResultSubtitle(result) || "No metadata yet"}</small>
              </span>
              <span class="search-row-meta">{getMetric(result)}</span>
            </button>
          {/each}
        </div>
      </section>
    {/each}
  {:else if query.trim().length >= 2}
    <p class="search-copy">No live aircraft, flights or airport entities matched this search yet.</p>
  {:else}
    <p class="search-copy">Type at least two characters to search aircraft, flights, airports, airlines, routes and saved locations.</p>
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

  .search-row:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.24);
    background: linear-gradient(180deg, rgba(44, 37, 18, 0.98) 0%, rgba(23, 22, 17, 0.98) 100%);
  }

  .search-row.active {
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
    padding: 0.24rem 0.5rem;
    border-radius: 999px;
    font-size: 0.67rem;
    font-weight: 800;
    color: #dfe6ef;
    background: rgba(255, 255, 255, 0.08);
    white-space: nowrap;
  }
 </style>
