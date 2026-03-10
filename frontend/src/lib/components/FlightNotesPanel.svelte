<script>
  export let flight;
  export let annotation = { notes: "", tags: [] };
  export let tagDraft = "";
  export let operatorCode = "N/A";
  export let bookmarked = false;
  export let onToggleBookmark = () => {};
  export let onAddCallsignAlert = () => {};
  export let onAddAirlineAlert = () => {};
  export let onAddRegistrationAlert = () => {};
  export let onAddTypeAlert = () => {};
  export let onAddIcao24Alert = () => {};
  export let onNotesChange = () => {};
  export let onTagDraftChange = () => {};
  export let onSubmitTag = () => {};
  export let onRemoveTag = () => {};

  $: callsignLabel = flight
    ? flight.callsign ?? flight.registration ?? flight.icao24?.toUpperCase() ?? "Selected aircraft"
    : "Selected aircraft";

  function handleTagKeydown(event) {
    if (event.key === "Enter") {
      onSubmitTag();
    }
  }
</script>

<section class="aircraft-notes-panel">
  <div class="workflow-header">
    <div>
      <p class="workflow-eyebrow">Product workflow</p>
      <h2>Notes and alerts</h2>
    </div>
    <span class="workflow-status">{annotation.tags.length} tags</span>
  </div>

  <p class="notes-caption">Private notes and quick alerts for {callsignLabel}.</p>

  <div class="local-tool-actions">
    <button class="workflow-button" type="button" on:click={onToggleBookmark}>
      {bookmarked ? "Remove tracked aircraft" : "Bookmark aircraft"}
    </button>
    {#if flight?.callsign}
      <button class="workflow-button" type="button" on:click={onAddCallsignAlert}>
        Alert by callsign
      </button>
    {/if}
    {#if operatorCode !== "N/A"}
      <button class="workflow-button" type="button" on:click={onAddAirlineAlert}>
        Alert by airline
      </button>
    {/if}
    {#if flight?.registration}
      <button class="workflow-button" type="button" on:click={onAddRegistrationAlert}>
        Alert by registration
      </button>
    {/if}
    {#if flight?.type_code}
      <button class="workflow-button" type="button" on:click={onAddTypeAlert}>
        Alert by type
      </button>
    {/if}
    {#if flight?.icao24}
      <button class="workflow-button" type="button" on:click={onAddIcao24Alert}>
        Alert by ICAO24
      </button>
    {/if}
  </div>

  <label class="notes-field">
    <span>Notes</span>
    <textarea
      rows="7"
      placeholder="Why this aircraft matters, route patterns, interesting behaviour..."
      value={annotation.notes}
      on:input={(event) => onNotesChange(event.currentTarget.value)}
    ></textarea>
  </label>

  <div class="tag-editor">
    <div class="tag-editor-header">
      <span>Tags</span>
      <small>{annotation.tags.length} saved</small>
    </div>

    {#if annotation.tags.length}
      <div class="tag-list">
        {#each annotation.tags as tag}
          <button class="tag-pill" type="button" on:click={() => onRemoveTag(tag)}>
            <span>{tag}</span>
            <strong>×</strong>
          </button>
        {/each}
      </div>
    {:else}
      <p class="notes-empty">No tags yet. Add route, airline, mission or spotting notes.</p>
    {/if}

    <div class="tag-input-row">
      <input
        type="text"
        placeholder="cargo, retro livery, frequent arrival..."
        value={tagDraft}
        on:input={(event) => onTagDraftChange(event.currentTarget.value)}
        on:keydown={handleTagKeydown}
      />
      <button class="workflow-button primary" type="button" on:click={onSubmitTag}>
        Add tag
      </button>
    </div>
  </div>
</section>

<style>
  .aircraft-notes-panel,
  .local-tool-actions,
  .notes-field,
  .tag-editor {
    display: grid;
    gap: 0.75rem;
  }

  .workflow-header {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: start;
  }

  .workflow-header h2,
  .workflow-header p,
  .notes-empty,
  .notes-caption {
    margin: 0;
  }

  .workflow-eyebrow {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: rgba(190, 203, 217, 0.62);
    margin-bottom: 0.2rem;
  }

  .workflow-status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.34rem 0.62rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 800;
    color: #f8de88;
    background: rgba(245, 185, 8, 0.12);
    border: 1px solid rgba(245, 185, 8, 0.22);
  }

  .notes-caption {
    color: rgba(190, 203, 217, 0.76);
    font-size: 0.8rem;
    line-height: 1.5;
  }

  .local-tool-actions {
    grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr));
  }

  .workflow-button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.78rem 0.84rem;
    font: inherit;
    font-weight: 700;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .workflow-button.primary {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .notes-field {
    gap: 0.34rem;
  }

  .notes-field span,
  .tag-editor-header span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(171, 186, 202, 0.62);
  }

  .notes-field textarea,
  .tag-editor {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    background:
      linear-gradient(180deg, rgba(31, 34, 39, 0.98) 0%, rgba(19, 21, 25, 0.98) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.02),
      0 14px 26px rgba(0, 0, 0, 0.2);
  }

  .notes-field textarea {
    min-height: 10rem;
    padding: 0.82rem 0.86rem;
    color: #eef3f8;
    box-sizing: border-box;
  }

  .tag-editor {
    gap: 0.65rem;
    padding: 0.78rem 0.82rem;
  }

  .tag-editor-header {
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    align-items: center;
  }

  .tag-editor-header small,
  .notes-empty {
    color: rgba(190, 203, 217, 0.74);
    font-size: 0.76rem;
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.38rem;
  }

  .tag-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.38rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.34rem 0.4rem 0.34rem 0.62rem;
    font: inherit;
    font-size: 0.73rem;
    font-weight: 700;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
  }

  .tag-pill strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.05rem;
    height: 1.05rem;
    border-radius: 999px;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .tag-input-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.45rem;
  }

  .tag-input-row input {
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.72rem 0.76rem;
    font: inherit;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
    box-sizing: border-box;
  }
</style>
