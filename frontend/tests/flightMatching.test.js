import assert from "node:assert/strict";
import test from "node:test";

import {
  deriveOperatorCode,
  matchesAirportTrafficFilter,
  matchesFlightSearch,
} from "../src/lib/utils/flightMatching.js";

test("deriveOperatorCode prefers explicit operator metadata", () => {
  assert.equal(
    deriveOperatorCode({
      operator_code: "lot",
      callsign: "ABC123",
    }),
    "LOT"
  );
  assert.equal(
    deriveOperatorCode({
      airline_code: "ual",
    }),
    "UAL"
  );
});

test("deriveOperatorCode falls back to the callsign prefix", () => {
  assert.equal(deriveOperatorCode({ callsign: "lot285 " }), "LOT");
  assert.equal(deriveOperatorCode("fdx90"), "FDX");
  assert.equal(deriveOperatorCode({ callsign: "12AB" }), "");
});

test("matchesFlightSearch includes enriched route and airport fields", () => {
  const flight = {
    icao24: "abc123",
    callsign: "LOT285",
    route_label: "WAW-JFK",
    route_verbose: "Warsaw -> New York JFK",
    airport_codes: "EPWA-KJFK",
    destination_name: "John F Kennedy International",
  };

  assert.equal(matchesFlightSearch(flight, "jfk"), true);
  assert.equal(matchesFlightSearch(flight, "epwa"), true);
  assert.equal(matchesFlightSearch(flight, "warsaw"), true);
  assert.equal(matchesFlightSearch(flight, "heathrow"), false);
  assert.equal(matchesFlightSearch(flight, ""), true);
});

test("matchesAirportTrafficFilter respects arrivals and departures", () => {
  const flight = {
    origin: "WAW",
    origin_icao: "EPWA",
    destination: "JFK",
    destination_icao: "KJFK",
  };

  assert.equal(matchesAirportTrafficFilter(flight, "waw", "all"), true);
  assert.equal(matchesAirportTrafficFilter(flight, "epwa", "departures"), true);
  assert.equal(matchesAirportTrafficFilter(flight, "epwa", "arrivals"), false);
  assert.equal(matchesAirportTrafficFilter(flight, "kjfk", "arrivals"), true);
  assert.equal(matchesAirportTrafficFilter(flight, "lhr", "all"), false);
  assert.equal(matchesAirportTrafficFilter(flight, "", "arrivals"), true);
});
