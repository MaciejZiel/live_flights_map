import { writable } from "svelte/store";

import { fetchFlights } from "../api/flights.js";

const REFRESH_INTERVAL_MS = Number(import.meta.env.VITE_REFRESH_INTERVAL_MS ?? 12000);
const BBOX_PRECISION = 4;

const initialState = {
  status: "idle",
  flights: [],
  error: null,
  fetchedAt: null,
  count: 0,
  bbox: null,
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

  async function refresh() {
    update((state) => ({
      ...state,
      status: state.flights.length ? "refreshing" : "loading",
      error: null,
    }));

    try {
      const payload = await fetchFlights(currentBbox);
      set({
        status: "success",
        flights: payload.flights ?? [],
        error: null,
        fetchedAt: payload.fetched_at ?? null,
        count: payload.count ?? 0,
        bbox: payload.bbox ?? null,
      });
    } catch (error) {
      update((state) => ({
        ...state,
        status: "error",
        error: error instanceof Error ? error.message : "Unknown error.",
      }));
    }
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
      refresh();
    }
  }

  function start() {
    if (poller) {
      return;
    }

    refresh();
    poller = window.setInterval(refresh, REFRESH_INTERVAL_MS);
  }

  function stop() {
    if (!poller) {
      return;
    }

    window.clearInterval(poller);
    poller = null;
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
