// A 304 Not Modified answer to the conditional /api/flights request means the
// snapshot the store already holds (possibly hydrated from localStorage) is
// identical to the server's current one. The server's ETag covers the payload
// meta (source, stale, reason, warning), so the cached meta is authoritative
// and any local "reconnecting" or "cached snapshot" state must be dropped.
export function confirmCachedSnapshot(state, cachedMeta, transport) {
  const meta = cachedMeta && typeof cachedMeta === "object" ? cachedMeta : {};

  return {
    ...state,
    status: "success",
    error: null,
    source: meta.source ?? "live",
    warning: meta.warning ?? null,
    stale: meta.stale ?? false,
    reason: meta.reason ?? "live",
    transport,
  };
}
