import { writable } from "svelte/store";

import { buildFlightsStreamUrl, fetchFlights, fetchLocalFlights } from "../api/flights.js";
import { buildLocalRegionTile } from "../utils/flightCoverage.js";

const REFRESH_INTERVAL_MS = Number(import.meta.env.VITE_REFRESH_INTERVAL_MS ?? 30000);
const BBOX_PRECISION = 4;
const USE_SSE = import.meta.env.VITE_USE_SSE === "true";
const SNAPSHOT_STORAGE_KEY = "live-flights-map.snapshot.v4";
const WORLD_BBOX = Object.freeze({ lamin: -90, lamax: 90, lomin: -180, lomax: 180 });
const LOCAL_REGION_CACHE_TTL_MS = 5 * 60 * 1000;
const LOCAL_REGION_CACHE_MAX_TILES = 64;

const initialState = {
  status: "idle",
  flights: [],
  error: null,
  fetchedAt: null,
  count: 0,
  bbox: null,
  source: "live",
  warning: null,
  stale: false,
  reason: "live",
  transport: USE_SSE ? "sse" : "polling",
  meta: {},
};

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function sanitizeStoredSnapshot(payload) {
  if (!isPlainObject(payload)) {
    return null;
  }

  return {
    flights: Array.isArray(payload.flights) ? payload.flights : [],
    fetched_at: typeof payload.fetched_at === "string" ? payload.fetched_at : null,
    count: Number.isFinite(payload.count) ? payload.count : 0,
    bbox: isPlainObject(payload.bbox) ? payload.bbox : null,
    meta: isPlainObject(payload.meta) ? payload.meta : {},
    etag: typeof payload.etag === "string" ? payload.etag : null,
    regionalTiles: Array.isArray(payload.regionalTiles) ? payload.regionalTiles : [],
  };
}

function normalizeBbox(bbox) {
  if (!bbox) {
    return null;
  }

  return {
    lamin: Number(bbox.lamin.toFixed(BBOX_PRECISION)),
    lamax: Number(bbox.lamax.toFixed(BBOX_PRECISION)),
    lomin: Number(bbox.lomin.toFixed(BBOX_PRECISION)),
    lomax: Number(bbox.lomax.toFixed(BBOX_PRECISION)),
  };
}

function sameBbox(left, right) {
  if (left === right) {
    return true;
  }

  if (!left || !right) {
    return false;
  }

  return (
    left.lamin === right.lamin &&
    left.lamax === right.lamax &&
    left.lomin === right.lomin &&
    left.lomax === right.lomax
  );
}

function loadStoredSnapshot() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const rawValue = window.localStorage.getItem(SNAPSHOT_STORAGE_KEY);
    return rawValue ? sanitizeStoredSnapshot(JSON.parse(rawValue)) : null;
  } catch {
    return null;
  }
}

function saveStoredSnapshot(payload) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(SNAPSHOT_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore storage write failures and keep the live store functional.
  }
}

function createFlightsStore() {
  const { subscribe, set, update } = writable(initialState);
  let poller = null;
  let viewBbox = null;
  let eventSource = null;
  let streamClosedManually = false;
  const storedSnapshot = loadStoredSnapshot();
  let snapshotEtag = storedSnapshot?.etag ?? null;
  let regionalTiles = new Map(
    (storedSnapshot?.regionalTiles ?? [])
      .filter(
        (tile) =>
          tile &&
          typeof tile.key === "string" &&
          Number.isFinite(tile.fetchedAt) &&
          isPlainObject(tile.bbox) &&
          Array.isArray(tile.flights)
      )
      .map((tile) => [tile.key, tile])
  );
  const inFlightRegionalTiles = new Set();
  const storedRegionalIcao24s = new Set(
    [...regionalTiles.values()].flatMap((tile) => tile.flights.map((flight) => flight?.icao24).filter(Boolean))
  );
  let globalPayload = storedSnapshot
    ? {
        ...storedSnapshot,
        flights: storedSnapshot.flights.filter((flight) => !storedRegionalIcao24s.has(flight?.icao24)),
        count: storedSnapshot.flights.filter((flight) => !storedRegionalIcao24s.has(flight?.icao24)).length,
      }
    : null;

  if (storedSnapshot?.flights?.length) {
    set({
      status: "success",
      flights: storedSnapshot.flights ?? [],
      error: null,
      fetchedAt: storedSnapshot.fetched_at ?? null,
      count: storedSnapshot.count ?? 0,
      bbox: storedSnapshot.bbox ?? null,
      source: storedSnapshot.meta?.source ?? "cache",
      warning: "Showing the last locally cached snapshot while live data reconnects.",
      stale: true,
      reason: "local_cache",
      transport: USE_SSE ? "sse" : "polling",
      meta: storedSnapshot.meta ?? {},
    });
  }

  function mergeRegionalTiles(payload) {
    const flightsById = new Map(
      (payload.flights ?? []).filter((flight) => flight?.icao24).map((flight) => [flight.icao24, flight])
    );
    const nowTimestamp = Date.now();
    let supplementalCount = 0;

    for (const [key, tile] of regionalTiles) {
      if (nowTimestamp - tile.fetchedAt > LOCAL_REGION_CACHE_TTL_MS) {
        regionalTiles.delete(key);
        continue;
      }
      for (const flight of tile.flights) {
        if (!flight?.icao24) {
          continue;
        }
        const existingFlight = flightsById.get(flight.icao24);
        const existingTime = Number(existingFlight?.last_contact ?? 0);
        const candidateTime = Number(flight.last_contact ?? 0);
        if (!existingFlight) {
          supplementalCount += 1;
          flightsById.set(flight.icao24, flight);
        } else if (candidateTime > existingTime) {
          flightsById.set(flight.icao24, flight);
        }
      }
    }

    return {
      ...payload,
      flights: [...flightsById.values()],
      count: flightsById.size,
      meta: {
        ...(payload.meta ?? {}),
        regional_supplement_count: supplementalCount,
        regional_supplement_tiles: regionalTiles.size,
      },
    };
  }

  function persistSnapshot(payload) {
    saveStoredSnapshot({
      ...payload,
      etag: snapshotEtag,
      regionalTiles: [...regionalTiles.values()],
    });
  }

  async function refreshLocalRegion(tile) {
    const cachedTile = regionalTiles.get(tile.key);
    const nowTimestamp = Date.now();
    if (cachedTile && nowTimestamp - cachedTile.fetchedAt < LOCAL_REGION_CACHE_TTL_MS) {
      regionalTiles.delete(tile.key);
      regionalTiles.set(tile.key, cachedTile);
      return;
    }
    if (inFlightRegionalTiles.has(tile.key)) {
      return;
    }

    inFlightRegionalTiles.add(tile.key);
    try {
      const result = await fetchLocalFlights(tile.bbox);
      if (result.notModified) {
        return;
      }
      regionalTiles.delete(tile.key);
      regionalTiles.set(tile.key, {
        key: tile.key,
        bbox: tile.bbox,
        fetchedAt: Date.now(),
        flights: result.payload.flights ?? [],
      });
      while (regionalTiles.size > LOCAL_REGION_CACHE_MAX_TILES) {
        regionalTiles.delete(regionalTiles.keys().next().value);
      }

      update((state) => {
        const combinedPayload = mergeRegionalTiles(globalPayload ?? state);
        persistSnapshot(combinedPayload);
        return {
          ...state,
          flights: combinedPayload.flights,
          count: combinedPayload.count,
          meta: combinedPayload.meta ?? state.meta,
        };
      });
    } catch {
      // Keep the world snapshot visible if the regional provider is unavailable.
    } finally {
      inFlightRegionalTiles.delete(tile.key);
    }
  }

  function applyPayload(payload, transport, etag = null) {
    if (transport === "polling") {
      snapshotEtag = etag;
    }
    globalPayload = payload;
    const combinedPayload = mergeRegionalTiles(payload);
    persistSnapshot(combinedPayload);
    set({
      status: "success",
      flights: combinedPayload.flights ?? [],
      error: null,
      fetchedAt: combinedPayload.fetched_at ?? null,
      count: combinedPayload.count ?? 0,
      bbox: viewBbox ?? combinedPayload.bbox ?? null,
      source: combinedPayload.meta?.source ?? "live",
      warning: combinedPayload.meta?.warning ?? null,
      stale: combinedPayload.meta?.stale ?? false,
      reason: combinedPayload.meta?.reason ?? "live",
      transport,
      meta: combinedPayload.meta ?? {},
    });
  }

  async function refresh(transport = "polling") {
    update((state) => ({
      ...state,
      status: state.flights.length ? "refreshing" : "loading",
      error: null,
      transport,
    }));

    try {
      const result = await fetchFlights(WORLD_BBOX, { etag: snapshotEtag });
      if (result.notModified) {
        update((state) => ({
          ...state,
          status: "success",
          error: null,
          transport,
        }));
        return;
      }
      applyPayload(result.payload, transport, result.etag);
    } catch (error) {
      update((state) => ({
        ...state,
        status: state.flights.length ? "success" : "error",
        error: state.flights.length ? null : error instanceof Error ? error.message : "Unknown error.",
        warning: state.flights.length
          ? error instanceof Error
            ? `${error.message} Showing the most recent cached snapshot.`
            : "Showing the most recent cached snapshot."
          : null,
        stale: state.flights.length ? true : state.stale,
        source: state.flights.length ? "cache" : state.source,
        reason: state.flights.length ? "local_cache" : "error",
        transport,
        meta: state.meta ?? {},
      }));
    }
  }

  function stopPolling() {
    if (!poller) {
      return;
    }

    window.clearInterval(poller);
    poller = null;
  }

  function startPolling() {
    if (poller) {
      return;
    }

    closeStream();
    refresh("polling");
    poller = window.setInterval(() => refresh("polling"), REFRESH_INTERVAL_MS);
  }

  function closeStream() {
    if (!eventSource) {
      return;
    }

    streamClosedManually = true;
    eventSource.close();
    eventSource = null;
  }

  function connectStream() {
    if (!USE_SSE || typeof window === "undefined" || typeof window.EventSource === "undefined") {
      startPolling();
      return;
    }

    stopPolling();
    closeStream();

    update((state) => ({
      ...state,
      status: state.flights.length ? "refreshing" : "loading",
      error: null,
      transport: "sse",
    }));

    streamClosedManually = false;
    eventSource = new window.EventSource(buildFlightsStreamUrl(WORLD_BBOX));

    eventSource.addEventListener("snapshot", (event) => {
      try {
        const payload = JSON.parse(event.data);
        applyPayload(payload, "sse");
      } catch {
        update((state) => ({
          ...state,
          status: "error",
          error: "Received an invalid SSE payload.",
          reason: "error",
          transport: "sse",
        }));
      }
    });

    eventSource.addEventListener("upstream_error", (event) => {
      try {
        const payload = JSON.parse(event.data);
        update((state) => ({
          ...state,
          status: state.flights.length ? "success" : "error",
          error: state.flights.length ? null : payload.error ?? "Live stream error.",
          warning: state.flights.length
            ? `${payload.error ?? "Live stream error."} Showing the most recent cached snapshot.`
            : null,
          stale: state.flights.length ? true : state.stale,
          source: state.flights.length ? "cache" : state.source,
          reason: state.flights.length ? "local_cache" : "error",
          transport: "sse",
        }));
      } catch {
        update((state) => ({
          ...state,
          status: state.flights.length ? "success" : "error",
          error: state.flights.length ? null : "Live stream error.",
          warning: state.flights.length
            ? "Live stream error. Showing the most recent cached snapshot."
            : null,
          stale: state.flights.length ? true : state.stale,
          source: state.flights.length ? "cache" : state.source,
          reason: state.flights.length ? "local_cache" : "error",
          transport: "sse",
        }));
      }
    });

    eventSource.onerror = () => {
      if (streamClosedManually) {
        streamClosedManually = false;
        return;
      }

      closeStream();
      update((state) => ({
        ...state,
        warning:
          state.warning ?? "Live stream disconnected. Falling back to interval polling.",
        transport: "polling",
      }));
      startPolling();
    };
  }

  function setBbox(nextBbox, zoom) {
    const normalizedBbox = normalizeBbox(nextBbox);
    const bboxChanged = !sameBbox(viewBbox, normalizedBbox);
    if (bboxChanged) {
      viewBbox = normalizedBbox;
      update((state) => ({
        ...state,
        bbox: normalizedBbox,
      }));
    }

    const tile = buildLocalRegionTile(normalizedBbox, zoom);
    if (tile) {
      void refreshLocalRegion(tile);
    }
  }

  function start() {
    if (poller || eventSource) {
      return;
    }

    connectStream();
  }

  function stop() {
    closeStream();
    stopPolling();
  }

  return {
    subscribe,
    refresh,
    setBbox,
    start,
    stop,
  };
}

export const flightsStore = createFlightsStore();
