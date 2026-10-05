import { writable } from "svelte/store";

import { buildFlightsStreamUrl, fetchFlights } from "../api/flights.js";

const REFRESH_INTERVAL_MS = Number(import.meta.env.VITE_REFRESH_INTERVAL_MS ?? 30000);
const BBOX_PRECISION = 4;
const USE_SSE = import.meta.env.VITE_USE_SSE === "true";
const SNAPSHOT_STORAGE_KEY = "live-flights-map.snapshot.v4";
const WORLD_BBOX = Object.freeze({ lamin: -90, lamax: 90, lomin: -180, lomax: 180 });

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

  function applyPayload(payload, transport, etag = null) {
    if (transport === "polling") {
      snapshotEtag = etag;
    }
    saveStoredSnapshot({ ...payload, etag: snapshotEtag });
    set({
      status: "success",
      flights: payload.flights ?? [],
      error: null,
      fetchedAt: payload.fetched_at ?? null,
      count: payload.count ?? 0,
      bbox: viewBbox ?? payload.bbox ?? null,
      source: payload.meta?.source ?? "live",
      warning: payload.meta?.warning ?? null,
      stale: payload.meta?.stale ?? false,
      reason: payload.meta?.reason ?? "live",
      transport,
      meta: payload.meta ?? {},
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

  function setBbox(nextBbox) {
    const normalizedBbox = normalizeBbox(nextBbox);
    if (sameBbox(viewBbox, normalizedBbox)) {
      return;
    }

    viewBbox = normalizedBbox;
    update((state) => ({
      ...state,
      bbox: normalizedBbox,
    }));
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
