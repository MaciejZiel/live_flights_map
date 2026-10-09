const PROVIDER_LABELS = {
  adsb_lol: "ADSB.lol",
  opensky: "OpenSky",
  demo: "Synthetic demo",
};

export function formatCooldownDuration(seconds) {
  const remaining = Math.max(0, Math.ceil(Number(seconds) || 0));
  if (remaining <= 0) {
    return null;
  }
  if (remaining < 60) {
    return `${remaining}s`;
  }
  if (remaining < 3600) {
    return `${Math.ceil(remaining / 60)}m`;
  }

  const hours = Math.floor(remaining / 3600);
  const minutes = Math.ceil((remaining % 3600) / 60);
  return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
}

export function buildProviderStatus(meta = {}, nowTimestamp = Date.now()) {
  const configured = Array.isArray(meta.providers_configured)
    ? meta.providers_configured.map((provider) => PROVIDER_LABELS[provider] ?? provider).filter(Boolean)
    : [];
  const providerUsed = meta.provider_used
    ? PROVIDER_LABELS[meta.provider_used] ?? meta.provider_used
    : null;
  const globalSource = providerUsed ?? (configured.join(" + ") || "Flight providers");
  const localCount = Math.max(0, Number(meta.regional_supplement_count) || 0);
  const localTiles = Math.max(0, Number(meta.regional_supplement_tiles) || 0);
  const regionalSource = meta.demo?.synthetic
    ? "Synthetic, no regional lookups"
    : localCount
    ? `ADSB.lol +${localCount} local`
    : localTiles
      ? "ADSB.lol local cache"
      : "ADSB.lol at zoom 6+";

  const cooldowns = Object.entries(meta.provider_cooldowns ?? {})
    .map(([provider, seconds]) => {
      const observedAt = Number(meta.provider_cooldowns_observed_at?.[provider]);
      const elapsed = Number.isFinite(observedAt) ? Math.max(0, (nowTimestamp - observedAt) / 1000) : 0;
      const duration = formatCooldownDuration(Number(seconds) - elapsed);
      if (!duration) {
        return null;
      }
      return `${PROVIDER_LABELS[provider] ?? provider} retry ~${duration}`;
    })
    .filter(Boolean);
  const compactCooldowns = cooldowns.map((cooldown) => cooldown.replace(" retry ~", " ~"));
  const compactRegional = meta.demo?.synthetic
    ? "Synthetic only"
    : localCount
      ? `Local +${localCount}`
      : "Local ADS-B at zoom 6+";

  return {
    globalSource,
    regionalSource,
    cooldowns,
    summary: [globalSource, regionalSource, ...cooldowns].join(" · "),
    compactRegional: [compactRegional, ...compactCooldowns].join(" · "),
  };
}
