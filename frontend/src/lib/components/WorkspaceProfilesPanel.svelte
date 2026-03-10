<script>
  export let accounts = [];
  export let activeAccountId = null;
  export let profiles = [];
  export let activeProfileId = null;
  export let syncStatus = "idle";
  export let updatedAt = null;
  export let accountDraftName = "";
  export let accountDraftEmail = "";
  export let draftName = "";
  export let draftRole = "analyst";
  export let syncError = null;
  export let onSelectAccount = () => {};
  export let onAccountDraftChange = () => {};
  export let onAccountEmailChange = () => {};
  export let onCreateAccount = () => {};
  export let onSelectProfile = () => {};
  export let onDraftChange = () => {};
  export let onRoleChange = () => {};
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

  function formatRole(value) {
    if (!value) {
      return "Analyst";
    }

    const normalized = String(value).trim().toLowerCase();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }

  function formatAccountSubtitle(account) {
    if (!account) {
      return "Workspace account";
    }

    if (account.email) {
      return account.email;
    }

    const profileCount = Number(account.profile_count ?? 0);
    return `${profileCount} ${profileCount === 1 ? "profile" : "profiles"}`;
  }
</script>

<section class="workspace-panel">
  <div class="workspace-header">
    <div>
      <p>Synced workspace</p>
      <h2>Accounts and profiles</h2>
    </div>
    <span class:danger={syncStatus === "error"} class="sync-pill">{syncStatus}</span>
  </div>

  <p class="workspace-copy">
    Active account and desk profile sync bookmarks, filters, replay sessions and notes to the backend workspace store.
    Last sync: {formatUpdatedAt(updatedAt)}
  </p>

  {#if syncError}
    <p class="workspace-copy workspace-error">{syncError}</p>
  {/if}

  <div class="account-list">
    {#each accounts as account}
      <button
        class:active={account.id === activeAccountId}
        class="profile-row account-row"
        type="button"
        on:click={() => onSelectAccount(account.id)}
      >
        <span class="profile-main">
          <strong>{account.display_name}</strong>
          <small>{formatAccountSubtitle(account)}</small>
        </span>
        <span class="profile-meta">
          <span class="profile-role">Account</span>
          <span class="profile-badge">{account.id === activeAccountId ? "Active" : "Open"}</span>
        </span>
      </button>
    {/each}
  </div>

  <div class="account-create">
    <input
      type="text"
      placeholder="New account"
      value={accountDraftName}
      on:input={(event) => onAccountDraftChange(event.currentTarget.value)}
      on:keydown={(event) => event.key === "Enter" && onCreateAccount()}
    />
    <input
      type="email"
      placeholder="ops@example.com"
      value={accountDraftEmail}
      on:input={(event) => onAccountEmailChange(event.currentTarget.value)}
      on:keydown={(event) => event.key === "Enter" && onCreateAccount()}
    />
    <button type="button" on:click={onCreateAccount}>Create account</button>
  </div>

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
        <span class="profile-meta">
          <span class="profile-role">{formatRole(profile.role)}</span>
          <span class="profile-badge">{profile.id === activeProfileId ? "Active" : "Open"}</span>
        </span>
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
    <select value={draftRole} on:change={(event) => onRoleChange(event.currentTarget.value)}>
      <option value="viewer">Viewer</option>
      <option value="analyst">Analyst</option>
      <option value="admin">Admin</option>
    </select>
    <button type="button" on:click={onCreateProfile}>Create</button>
  </div>
</section>

<style>
  .workspace-panel,
  .profile-list,
  .account-list {
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
  .profile-role,
  .profile-create button,
  .account-create button {
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

  .account-row:not(.active) {
    background: rgba(90, 120, 164, 0.08);
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

  .profile-meta {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .profile-role {
    min-height: 1.75rem;
    padding: 0 0.6rem;
    color: #d8e4f4;
    background: rgba(108, 135, 175, 0.22);
  }

  .profile-create,
  .account-create {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    gap: 0.45rem;
  }

  .account-create {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  }

  .profile-create input,
  .profile-create select,
  .profile-create button,
  .account-create input,
  .account-create button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    font: inherit;
  }

  .profile-create input,
  .profile-create select,
  .account-create input {
    border-radius: 12px;
    padding: 0.7rem 0.74rem;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
  }

  .profile-create select {
    min-width: 7.25rem;
  }

  .profile-create button,
  .account-create button {
    padding: 0 0.88rem;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    cursor: pointer;
  }

  @media (max-width: 720px) {
    .profile-create,
    .account-create {
      grid-template-columns: 1fr;
    }
  }
</style>
