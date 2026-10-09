import { expect, test } from "@playwright/test";

const CACHED_SNAPSHOT_WARNING = "Showing the last locally cached snapshot while live data reconnects.";
const SNAPSHOT_ETAG = '"snapshot-v1"';

const SNAPSHOT = {
  count: 1,
  fetched_at: "2026-03-11T10:00:00+00:00",
  bbox: { lamin: -90, lamax: 90, lomin: -180, lomax: 180 },
  flights: [
    {
      icao24: "48af06",
      callsign: "LOT123",
      origin_country: "Poland",
      latitude: 52.2297,
      longitude: 21.0122,
      altitude: 10972,
      velocity: 236,
      vertical_rate: 0,
      true_track: 284,
      on_ground: false,
      last_contact: 1760000000,
    },
  ],
  meta: {
    source: "collector_cache",
    stale: false,
    reason: "live",
    warning: null,
  },
};

async function mockApi(page, flightRequests) {
  await page.route("**/*", async (route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());
    if (!pathname.startsWith("/api/")) {
      await route.continue();
      return;
    }

    if (pathname === "/api/flights") {
      const ifNoneMatch = await request.headerValue("if-none-match");
      flightRequests.push(ifNoneMatch);
      if (ifNoneMatch === SNAPSHOT_ETAG) {
        await route.fulfill({ status: 304, headers: { ETag: SNAPSHOT_ETAG } });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { ETag: SNAPSHOT_ETAG },
        body: JSON.stringify(SNAPSHOT),
      });
      return;
    }

    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
}

test("a 304 revalidation clears the cached-snapshot warning after a reload", async ({ page }) => {
  const flightRequests = [];
  await mockApi(page, flightRequests);

  await page.goto("/");
  await expect.poll(() => flightRequests.length).toBeGreaterThanOrEqual(1);
  await expect(page.getByText(CACHED_SNAPSHOT_WARNING)).toHaveCount(0);

  // The snapshot (and its ETag) is now in localStorage. Reloading hydrates the
  // map from it and revalidates with If-None-Match; the server answers 304.
  flightRequests.length = 0;
  await page.reload();
  await expect.poll(() => flightRequests).toContain(SNAPSHOT_ETAG);

  await expect(page.getByText(CACHED_SNAPSHOT_WARNING)).toHaveCount(0);
});
