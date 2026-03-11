import test from "node:test";
import assert from "node:assert/strict";

import {
  buildFlightDetailsFallback,
  buildFlightDetailsKey,
  mergeFlightDetails,
  shouldRefreshCachedFlightDetails,
} from "../src/lib/utils/flightDetailsState.js";

const LIVE_FLIGHT = {
  icao24: "48af06",
  callsign: "lot123 ",
  registration: "sp-lvg",
  type_code: "B38M",
  origin_country: "Poland",
};

test("buildFlightDetailsKey normalizes callsign and registration", () => {
  assert.equal(buildFlightDetailsKey(LIVE_FLIGHT), "48af06:LOT123:SP-LVG");
});

test("buildFlightDetailsFallback keeps live identity and no-photo state", () => {
  const fallback = buildFlightDetailsFallback(LIVE_FLIGHT, "Waiting for route lookup.");

  assert.deepEqual(fallback.aircraft, {
    icao24: "48af06",
    callsign: "lot123 ",
    registration: "sp-lvg",
    type_code: "B38M",
    origin_country: "Poland",
    operator_code: "LOT",
  });
  assert.equal(fallback.meta.warning, "Waiting for route lookup.");
  assert.equal(fallback.meta.detail_quality.photo_state, "missing");
  assert.equal(fallback.meta.detail_quality.photo_label, "No aircraft photo");
  assert.equal(fallback.meta.detail_quality.route_state, "pending");
  assert.equal(fallback.meta.detail_quality.route_label, "Live track only");
});

test("mergeFlightDetails preserves fallback identity while enriching remote data", () => {
  const merged = mergeFlightDetails(LIVE_FLIGHT, {
    route: {
      airline_code: "LOT",
      flight_number: "123",
    },
    photo: {
      thumbnail_url: "https://example.com/photo.jpg",
      source: "Wikimedia Commons",
    },
    meta: {
      fetched_at: "2026-03-11T18:00:00+00:00",
      detail_quality: {
        band: "good",
        summary: "Resolved route with a representative aircraft photo.",
        photo_state: "representative",
        photo_label: "Representative aircraft photo",
        route_state: "resolved",
        route_label: "Verified route",
      },
    },
  });

  assert.equal(merged.aircraft.registration, "sp-lvg");
  assert.equal(merged.aircraft.operator_code, "LOT");
  assert.equal(merged.route.flight_number, "123");
  assert.equal(merged.photo.thumbnail_url, "https://example.com/photo.jpg");
  assert.equal(merged.meta.detail_quality.photo_state, "representative");
  assert.equal(merged.meta.detail_quality.photo_label, "Representative aircraft photo");
  assert.equal(merged.meta.detail_quality.route_label, "Verified route");
});

test("shouldRefreshCachedFlightDetails only retries when photo is still missing", () => {
  assert.equal(shouldRefreshCachedFlightDetails(null), true);
  assert.equal(
    shouldRefreshCachedFlightDetails({
      photo: null,
    }),
    true
  );
  assert.equal(
    shouldRefreshCachedFlightDetails({
      photo: {
        thumbnail_url: "https://example.com/photo.jpg",
      },
    }),
    false
  );
});
