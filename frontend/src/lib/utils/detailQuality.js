function parseAgeSeconds(value) {
  const normalizedValue = String(value ?? "").trim().toLowerCase();
  const match = normalizedValue.match(/^(\d+)s old$/);
  if (!match) {
    return null;
  }

  return Number.parseInt(match[1], 10);
}

export function getRouteQualityMeta(detailQuality, detailsStatus) {
  const routeConfidence = detailQuality?.route_confidence ?? null;
  const routeState = detailQuality?.route_state ?? null;

  if (routeConfidence === "verified" || routeState === "resolved") {
    return {
      label: "Verified route",
      note: "Resolved airport pair matches the current flight identity.",
      tone: "strong",
    };
  }

  if (routeConfidence === "tentative" || routeState === "unverified") {
    return {
      label: "Tentative route",
      note: "Looks plausible, but the route still needs confirmation.",
      tone: "soft",
    };
  }

  if (detailsStatus === "loading" || detailsStatus === "refreshing") {
    return {
      label: "Resolving route",
      note: "Showing live track first while route matching catches up.",
      tone: "muted",
    };
  }

  return {
    label: "Live track only",
    note: "No confirmed route match yet.",
    tone: "muted",
  };
}

export function getPhotoQualityMeta(detailQuality, hasPhoto) {
  const photoMatch = detailQuality?.photo_match ?? detailQuality?.photo_state ?? "missing";
  const photoSource = detailQuality?.photo_source ?? null;

  if (!hasPhoto || photoMatch === "missing") {
    return {
      label: "No photo yet",
      note: "Free photo sources do not have a usable match yet.",
      tone: "muted",
    };
  }

  if (photoMatch === "representative") {
    return {
      label: "Representative photo",
      note: photoSource
        ? `Matched from ${photoSource} for the same type or operator.`
        : "Matched for the same type or operator.",
      tone: "soft",
    };
  }

  return {
    label: "Exact aircraft photo",
    note: photoSource ? `Matched by registration from ${photoSource}.` : "Matched by registration.",
    tone: "strong",
  };
}

export function getFreshnessMeta({
  snapshotFreshness,
  detailFreshness,
  isReplayActive = false,
  detailsStatus = "idle",
  snapshotFeedLabel = "Live feed",
  snapshotTransport = "Polling",
}) {
  if (isReplayActive) {
    return {
      label: "Replay frame",
      note: `${snapshotFeedLabel} via ${snapshotTransport}.`,
      tone: "soft",
    };
  }

  const snapshotAgeSeconds = parseAgeSeconds(snapshotFreshness);
  const detailAgeSeconds = parseAgeSeconds(detailFreshness);
  const detailsSyncing = detailsStatus === "loading" || detailsStatus === "refreshing";

  if (snapshotAgeSeconds === null && detailsSyncing) {
    return {
      label: "Syncing now",
      note: "Waiting for the next live frame and refreshed details.",
      tone: "muted",
    };
  }

  if (snapshotAgeSeconds === null) {
    return {
      label: "Waiting for live data",
      note: "First live snapshot has not arrived yet.",
      tone: "muted",
    };
  }

  const label =
    snapshotAgeSeconds <= 20 ? "Fresh now" : snapshotAgeSeconds <= 90 ? "A little older" : "Cached snapshot";
  const detailPart =
    detailAgeSeconds === null ? (detailsSyncing ? "details syncing" : "details pending") : `details ${detailAgeSeconds}s old`;

  return {
    label,
    note: `Live frame ${snapshotAgeSeconds}s old, ${detailPart}.`,
    tone: snapshotAgeSeconds <= 20 ? "strong" : snapshotAgeSeconds <= 90 ? "soft" : "muted",
  };
}
