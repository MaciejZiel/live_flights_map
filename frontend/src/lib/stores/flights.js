import { writable } from "svelte/store";

import { buildFlightsStreamUrl, fetchFlights } from "../api/flights.js";

const REFRESH_INTERVAL_MS = Number(import.meta.env.VITE_REFRESH_INTERVAL_MS ?? 12000);
const BBOX_PRECISION = 4;
const BBOX_DEBOUNCE_MS = Number(import.meta.env.VITE_BBOX_DEBOUNCE_MS ?? 350);
const USE_SSE = import.meta.env.VITE_USE_SSE !== "false";

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
};

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

function createFlightsStore() {
  const { subscribe, set, update } = writable(initialState);
  let poller = null;
  let currentBbox = null;
  let bboxRefreshTimeout = null;
  let eventSource = null;
  let streamClosedManually = false;

  function applyPayload(payload, transport) {
    set({
      status: "success",
      flights: payload.flights ?? [],
      error: null,
      fetchedAt: payload.fetched_at ?? null,
      count: payload.count ?? 0,
      bbox: payload.bbox ?? null,
      source: payload.meta?.source ?? "live",
      warning: payload.meta?.warning ?? null,
      stale: payload.meta?.stale ?? false,
      reason: payload.meta?.reason ?? "live",
      transport,
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
      const payload = await fetchFlights(currentBbox);
      applyPayload(payload, transport);
    } catch (error) {
      update((state) => ({
        ...state,
        status: "error",
        error: error instanceof Error ? error.message : "Unknown error.",
        warning: null,
        reason: "error",
        transport,
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
    eventSource = new window.EventSource(buildFlightsStreamUrl(currentBbox));

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
          status: "error",
          error: payload.error ?? "Live stream error.",
          warning: null,
          reason: "error",
          transport: "sse",
        }));
      } catch {
        update((state) => ({
          ...state,
          status: "error",
          error: "Live stream error.",
          warning: null,
          reason: "error",
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
    if (sameBbox(currentBbox, normalizedBbox)) {
      return;
    }

    currentBbox = normalizedBbox;
    update((state) => ({
      ...state,
      bbox: normalizedBbox,
    }));

    if (poller) {
      if (bboxRefreshTimeout) {
        window.clearTimeout(bboxRefreshTimeout);
      }

      bboxRefreshTimeout = window.setTimeout(() => {
        bboxRefreshTimeout = null;
        refresh("polling");
      }, BBOX_DEBOUNCE_MS);
      return;
    }

    if (eventSource) {
      if (bboxRefreshTimeout) {
        window.clearTimeout(bboxRefreshTimeout);
      }

      bboxRefreshTimeout = window.setTimeout(() => {
        bboxRefreshTimeout = null;
        connectStream();
      }, BBOX_DEBOUNCE_MS);
    }
  }

  function start() {
    if (poller || eventSource) {
      return;
    }

    connectStream();
  }

  function stop() {
    if (bboxRefreshTimeout) {
      window.clearTimeout(bboxRefreshTimeout);
      bboxRefreshTimeout = null;
    }

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
