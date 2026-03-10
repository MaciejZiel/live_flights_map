<script>
  export let profiles = [];
  export let activeProfileId = null;
  export let syncStatus = "idle";
  export let updatedAt = null;
  export let draftName = "";
  export let syncError = null;
  export let onSelectProfile = () => {};
  export let onDraftChange = () => {};
  export let onCreateProfile = () => {};

  function formatUpdatedAt(value) {
    if (!value) {
      return "Never synced";
    }

    return new Intl.DateTimeFormat("pl-PL", {
      hour: "2-digit",
      minute: "2-digit",
      month: "short",
      day: "2-digit",
    }).format(new Date(value));
  }
</script>

<section class="workspace-panel">
  <div class="workspace-header">
    <div>
      <p>Synced workspace</p>
      <h2>Profiles</h2>
    </div>
    <span class:danger={syncStatus === "error"} class="sync-pill">{syncStatus}</span>
  </div>

  <p class="workspace-copy">
    Active profile syncs bookmarks, filters, replay sessions and notes to the backend workspace store.
    Last sync: {formatUpdatedAt(updatedAt)}
  </p>

  {#if syncError}
    <p class="workspace-copy workspace-error">{syncError}</p>
  {/if}

  <div class="profile-list">
    {#each profiles as profile}
      <button
        class:active={profile.id === activeProfileId}
        class="profile-row"
        type="button"
        on:click={() => onSelectProfile(profile.id)}
      >
        <span class="profile-main">
          <strong>{profile.display_name}</strong>
          <small>{new Intl.DateTimeFormat("pl-PL", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(profile.updated_at))}</small>
        </span>
        <span class="profile-badge">{profile.id === activeProfileId ? "Active" : "Open"}</span>
      </button>
    {/each}
  </div>

  <div class="profile-create">
    <input
      type="text"
      placeholder="New desk profile"
      value={draftName}
      on:input={(event) => onDraftChange(event.currentTarget.value)}
      on:keydown={(event) => event.key === "Enter" && onCreateProfile()}
    />
    <button type="button" on:click={onCreateProfile}>Create</button>
  </div>
</section>

<style>
  .workspace-panel,
  .profile-list {
    display: grid;
    gap: 0.6rem;
  }

  .workspace-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: start;
  }

  .workspace-header p,
  .workspace-header h2,
  .workspace-copy {
    margin: 0;
  }

  .workspace-header p {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: rgba(186, 197, 209, 0.66);
  }

  .workspace-header h2 {
    margin-top: 0.18rem;
    color: #f5f7fb;
    font-size: 1rem;
  }

  .workspace-copy {
    font-size: 0.74rem;
    line-height: 1.5;
    color: rgba(194, 203, 216, 0.78);
  }

  .workspace-error {
    color: #ffd6d6;
  }

  .sync-pill,
  .profile-badge,
  .profile-create button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 800;
  }

  .sync-pill {
    min-width: 3.5rem;
    min-height: 1.9rem;
    padding: 0 0.6rem;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.08);
  }

  .sync-pill.danger {
    color: #ffd6d6;
    background: rgba(122, 35, 35, 0.28);
  }

  .profile-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.6rem;
    align-items: center;
    width: 100%;
    padding: 0.78rem 0.82rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    font: inherit;
    color: inherit;
    background: rgba(255, 255, 255, 0.04);
    text-align: left;
    cursor: pointer;
  }

  .profile-row.active {
    border-color: rgba(245, 185, 8, 0.28);
    background: linear-gradient(180deg, rgba(51, 43, 14, 0.98) 0%, rgba(26, 24, 17, 0.98) 100%);
  }

  .profile-main {
    display: grid;
    gap: 0.14rem;
  }

  .profile-main strong {
    color: #f5f7fb;
    font-size: 0.84rem;
  }

  .profile-main small {
    color: rgba(194, 203, 216, 0.72);
    font-size: 0.72rem;
  }

  .profile-badge {
    min-width: 3.1rem;
    min-height: 1.75rem;
    padding: 0 0.55rem;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .profile-create {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.45rem;
  }

  .profile-create input,
  .profile-create button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    font: inherit;
  }

  .profile-create input {
    border-radius: 12px;
    padding: 0.7rem 0.74rem;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
  }

  .profile-create button {
    padding: 0 0.88rem;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    cursor: pointer;
  }

  @media (max-width: 720px) {
    .profile-create {
      grid-template-columns: 1fr;
    }
  }
</style>
