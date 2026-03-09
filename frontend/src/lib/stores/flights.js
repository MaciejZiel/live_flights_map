import { writable } from "svelte/store";

import { fetchFlights } from "../api/flights.js";

const REFRESH_INTERVAL_MS = Number(import.meta.env.VITE_REFRESH_INTERVAL_MS ?? 12000);

const initialState = {
  status: "idle",
  flights: [],
  error: null,
  fetchedAt: null,
  count: 0,
  bbox: null,
};

function createFlightsStore() {
  const { subscribe, set, update } = writable(initialState);
  let poller = null;

  async function refresh() {
    update((state) => ({
      ...state,
      status: state.flights.length ? "refreshing" : "loading",
      error: null,
    }));

    try {
      const payload = await fetchFlights();
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
    start,
    stop,
  };
}

export const flightsStore = createFlightsStore();
