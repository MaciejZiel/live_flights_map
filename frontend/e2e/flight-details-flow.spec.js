import { expect, test } from "@playwright/test";

const PNG_1X1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9l9wAAAABJRU5ErkJggg==",
  "base64"
);

const ACCOUNT = {
  id: "acc-1",
  display_name: "Ops Team",
  email: "ops@example.com",
  created_at: "2026-03-11T00:00:00+00:00",
  updated_at: "2026-03-11T00:00:00+00:00",
  profile_count: 1,
};

const PROFILE = {
  id: "profile-1",
  account_id: "acc-1",
  display_name: "Main Desk",
  role: "analyst",
  created_at: "2026-03-11T00:00:00+00:00",
  updated_at: "2026-03-11T00:00:00+00:00",
};

const DEFAULT_WORKSPACE_STATE = {
  filters: {},
  mapStyle: "standard",
  mapViewport: null,
  filterPresets: [],
  sortBy: "altitude_desc",
  theme: "dark",
  watchlist: [],
  watchModeEnabled: false,
  flightAnnotations: {},
  alertRules: [],
  alertEvents: [],
  monitoringSessions: [],
  savedViews: [],
  savedEntities: [],
  onboardingDismissed: true,
  aircraftClusteringEnabled: false,
  weatherLayerEnabled: false,
  showAirportMarkers: true,
  selectedAirportCode: null,
  selectedAirportHistoryHours: 12,
  replayAnchorTimestamp: null,
  replayWindowMinutes: 90,
  replayPlaybackSpeed: 1,
};

const VISIBLE_FLIGHTS = [
  {
    icao24: "48af06",
    callsign: "LOT123",
    registration: "SP-LVG",
    type_code: "B38M",
    origin_country: "Poland",
    latitude: 52.2297,
    longitude: 21.0122,
    altitude: 10972,
    velocity: 236,
    vertical_rate: 0,
    true_track: 284,
    on_ground: false,
    last_contact: 1760000000,
    route_label: "WAW -> LHR",
  },
  {
    icao24: "4242ab",
    callsign: "RYR456",
    registration: "EI-DCL",
    type_code: "B738",
    origin_country: "Ireland",
    latitude: 53.3498,
    longitude: -6.2603,
    altitude: 10200,
    velocity: 224,
    vertical_rate: -1.2,
    true_track: 93,
    on_ground: false,
    last_contact: 1760000002,
    route_label: "DUB -> STN",
  },
];

const SEARCH_INDEX = {
  LOT: [
    {
      entity_type: "flight",
      entity_key: "48af06",
      icao24: "48af06",
      callsign: "LOT123",
      registration: "SP-LVG",
      type_code: "B38M",
      origin_country: "Poland",
      label: "LOT123",
      subtitle: "SP-LVG · B38M · Poland",
    },
  ],
  RYR: [
    {
      entity_type: "flight",
      entity_key: "4242ab",
      icao24: "4242ab",
      callsign: "RYR456",
      registration: "EI-DCL",
      type_code: "B738",
      origin_country: "Ireland",
      label: "RYR456",
      subtitle: "EI-DCL · B738 · Ireland",
    },
  ],
};

const DETAILS_BY_ICAO24 = {
  "48af06": {
    aircraft: {
      icao24: "48af06",
      callsign: "LOT123",
      registration: "SP-LVG",
      type_code: "B38M",
      origin_country: "Poland",
      operator_code: "LOT",
    },
    route: {
      airline_code: "LO",
      airline_name: "LOT Polish Airlines",
      flight_number: "123",
      plausible: true,
      iata_codes: "WAW-LHR",
      airport_codes: "EPWA-EGLL",
      origin: {
        iata: "WAW",
        icao: "EPWA",
        name: "Warsaw Chopin",
        location: "Warsaw",
        latitude: 52.1657,
        longitude: 20.9671,
      },
      destination: {
        iata: "LHR",
        icao: "EGLL",
        name: "London Heathrow",
        location: "London",
        latitude: 51.47,
        longitude: -0.4543,
      },
      airports: [
        { iata: "WAW", icao: "EPWA", location: "Warsaw", latitude: 52.1657, longitude: 20.9671 },
        { iata: "LHR", icao: "EGLL", location: "London", latitude: 51.47, longitude: -0.4543 },
      ],
      stops: [],
    },
    photo: {
      thumbnail_url: "https://images.example.test/sp-lvg.png",
      link: "https://images.example.test/sp-lvg",
      source: "Wikimedia Commons",
      match_type: "registration",
    },
    meta: {
      fetched_at: "2026-03-11T10:00:00+00:00",
      warning: null,
      detail_quality: {
        band: "strong",
        score: 92,
        summary: "Resolved route with an exact aircraft photo.",
      },
    },
  },
  "4242ab": {
    aircraft: {
      icao24: "4242ab",
      callsign: "RYR456",
      registration: "EI-DCL",
      type_code: "B738",
      origin_country: "Ireland",
      operator_code: "RYR",
    },
    route: {
      airline_code: "FR",
      airline_name: "Ryanair",
      flight_number: "456",
      plausible: true,
      iata_codes: "DUB-STN",
      airport_codes: "EIDW-EGSS",
      origin: {
        iata: "DUB",
        icao: "EIDW",
        name: "Dublin",
        location: "Dublin",
        latitude: 53.4213,
        longitude: -6.2701,
      },
      destination: {
        iata: "STN",
        icao: "EGSS",
        name: "London Stansted",
        location: "London",
        latitude: 51.885,
        longitude: 0.235,
      },
      airports: [
        { iata: "DUB", icao: "EIDW", location: "Dublin", latitude: 53.4213, longitude: -6.2701 },
        { iata: "STN", icao: "EGSS", location: "London", latitude: 51.885, longitude: 0.235 },
      ],
      stops: [],
    },
    photo: {
      thumbnail_url: "https://images.example.test/ei-dcl.png",
      link: "https://images.example.test/ei-dcl",
      source: "Openverse",
      match_type: "registration",
    },
    meta: {
      fetched_at: "2026-03-11T10:01:00+00:00",
      warning: null,
      detail_quality: {
        band: "good",
        score: 86,
        summary: "Resolved route with an exact aircraft photo.",
      },
    },
  },
};

function buildWorkspaceState(overrides = {}) {
  return {
    ...DEFAULT_WORKSPACE_STATE,
    ...overrides,
  };
}

async function fulfillJson(route, payload) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

async function mockRadarApi(page) {
  let workspaceState = buildWorkspaceState();

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    if (!pathname.startsWith("/api/")) {
      await route.continue();
      return;
    }

    if (pathname === "/api/flights" && request.method() === "GET") {
      return fulfillJson(route, {
        count: VISIBLE_FLIGHTS.length,
        fetched_at: "2026-03-11T10:00:00+00:00",
        bbox: {
          lamin: 49.0,
          lamax: 55.1,
          lomin: 14.0,
          lomax: 24.5,
        },
        flights: VISIBLE_FLIGHTS,
        meta: {
          source: "live",
          stale: false,
          reason: "live",
          provider_used: "adsb_lol",
          providers_configured: ["adsb_lol"],
          quality: {
            summary: "Mocked live coverage for UI regression tests.",
          },
        },
      });
    }

    if (pathname === "/api/search" && request.method() === "GET") {
      const query = (url.searchParams.get("q") || "").toUpperCase();
      const results = Object.entries(SEARCH_INDEX)
        .filter(([key]) => query.includes(key))
        .flatMap(([, items]) => items);
      return fulfillJson(route, {
        count: results.length,
        results,
        groups: {
          flights: results,
        },
      });
    }

    if (pathname.startsWith("/api/flights/") && pathname.endsWith("/details")) {
      const icao24 = pathname.split("/")[3];
      return fulfillJson(route, DETAILS_BY_ICAO24[icao24] || { aircraft: { icao24 }, route: null, photo: null, meta: {} });
    }

    if (pathname === "/api/aircraft-photo") {
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: PNG_1X1,
      });
      return;
    }

    if (pathname === "/api/workspace/accounts") {
      return fulfillJson(route, {
        count: 1,
        accounts: [ACCOUNT],
      });
    }

    if (pathname === "/api/workspace/profiles") {
      return fulfillJson(route, {
        count: 1,
        account: ACCOUNT,
        profiles: [PROFILE],
      });
    }

    if (pathname === "/api/workspace/state" && request.method() === "GET") {
      return fulfillJson(route, {
        account: ACCOUNT,
        profile: PROFILE,
        state: workspaceState,
        updated_at: "2026-03-11T10:00:00+00:00",
      });
    }

    if (pathname === "/api/workspace/state" && request.method() === "PUT") {
      const payload = request.postDataJSON();
      workspaceState = buildWorkspaceState(payload?.state || {});
      return fulfillJson(route, {
        account: ACCOUNT,
        profile: PROFILE,
        state: workspaceState,
        updated_at: "2026-03-11T10:00:05+00:00",
      });
    }

    if (pathname === "/api/airports") {
      return fulfillJson(route, {
        count: 0,
        airports: [],
      });
    }

    if (pathname === "/api/traffic/leaderboard") {
      return fulfillJson(route, {
        count: 0,
        flights: [],
        meta: {
          coverage: "global",
          source: "mock",
          stale: false,
        },
      });
    }

    if (pathname === "/api/history/replay") {
      return fulfillJson(route, {
        count: 0,
        snapshots: [],
      });
    }

    return fulfillJson(route, {});
  });
}

test.beforeEach(async ({ page }) => {
  await mockRadarApi(page);
});

test("search result opens flight details with photo and alert action", async ({ page }) => {
  await page.goto("/");

  const searchInput = page.getByTestId("global-search-input");
  await expect(searchInput).toBeVisible();
  await searchInput.fill("LOT");

  const searchSuggestions = page.getByTestId("search-suggestions");
  await expect(searchSuggestions).toContainText("LOT123");
  await searchInput.press("ArrowDown");
  await searchInput.press("Enter");

  const detailsPanel = page.getByTestId("flight-details-panel");
  await expect(detailsPanel).toContainText("WAW -> LHR");
  await expect(detailsPanel).toContainText("SP-LVG");
  await expect(detailsPanel).toContainText("LOT Polish Airlines");
  await expect(page.getByTestId("flight-photo-image")).toBeVisible();
  await expect(page.getByTestId("flight-photo-image")).toHaveAttribute("src", /sp-lvg/i);

  await page.getByTestId("flight-add-alert").click();
  await expect
    .poll(async () => {
      return page.evaluate(() => {
        const rawValue = window.localStorage.getItem("live-flights-map.preferences.v4");
        if (!rawValue) {
          return 0;
        }
        try {
          const payload = JSON.parse(rawValue);
          return Array.isArray(payload.alertRules) ? payload.alertRules.length : 0;
        } catch {
          return 0;
        }
      });
    })
    .toBe(1);
});

test("changing selected flight refreshes inspector content and photo source", async ({ page }) => {
  await page.goto("/");

  const searchInput = page.getByTestId("global-search-input");
  await expect(searchInput).toBeVisible();

  await searchInput.fill("LOT");
  await expect(page.getByTestId("search-suggestions")).toContainText("LOT123");
  await searchInput.press("ArrowDown");
  await searchInput.press("Enter");
  await expect(page.getByTestId("flight-details-panel")).toContainText("SP-LVG");
  await expect(page.getByTestId("flight-photo-image")).toHaveAttribute("src", /sp-lvg/i);

  await searchInput.fill("RYR");
  await expect(page.getByTestId("search-suggestions")).toContainText("RYR456");
  await searchInput.press("ArrowDown");
  await searchInput.press("Enter");

  const detailsPanel = page.getByTestId("flight-details-panel");
  await expect(detailsPanel).toContainText("DUB -> STN");
  await expect(detailsPanel).toContainText("EI-DCL");
  await expect(detailsPanel).toContainText("Ryanair");
  await expect(page.getByTestId("flight-photo-image")).toHaveAttribute("src", /ei-dcl/i);
});

test("keyboard shortcuts keep search and inspector accessible without the mouse", async ({ page }) => {
  await page.goto("/");

  await page.keyboard.press("Shift+Slash");
  await expect(page.locator(".radar-left-panel")).not.toHaveClass(/compact/);

  await page.keyboard.press("Control+K");
  await expect(page.getByTestId("global-search-input")).toBeFocused();

  await page.keyboard.type("RYR");
  await expect(page.getByTestId("search-suggestions")).toContainText("RYR456");

  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("option", { name: /RYR456/i })).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("option", { name: /RYR456/i })).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(page.getByTestId("flight-details-panel")).toContainText("EI-DCL");

  await page.keyboard.press("i");
  await expect(page.locator(".radar-right-panel")).toBeFocused();
});
