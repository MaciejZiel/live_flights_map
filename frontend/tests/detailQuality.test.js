import test from "node:test";
import assert from "node:assert/strict";

import {
  getFreshnessMeta,
  getPhotoQualityMeta,
  getRouteQualityMeta,
} from "../src/lib/utils/detailQuality.js";

test("getRouteQualityMeta distinguishes verified and tentative routes", () => {
  assert.deepEqual(getRouteQualityMeta({ route_confidence: "verified" }, "success"), {
    label: "Verified",
    note: "Resolved airport pair matches the current flight identity.",
    tone: "strong",
  });

  assert.deepEqual(getRouteQualityMeta({ route_confidence: "tentative" }, "success"), {
    label: "Tentative",
    note: "Looks plausible, but the route still needs confirmation.",
    tone: "soft",
  });
});

test("getPhotoQualityMeta distinguishes exact and representative photos", () => {
  assert.deepEqual(
    getPhotoQualityMeta(
      {
        photo_match: "exact",
        photo_source: "Planespotting",
      },
      true
    ),
    {
      label: "Exact",
      note: "Matched by registration from Planespotting.",
      tone: "strong",
    }
  );

  assert.deepEqual(
    getPhotoQualityMeta(
      {
        photo_match: "representative",
        photo_source: "Wikimedia Commons",
      },
      true
    ),
    {
      label: "Representative",
      note: "Matched from Wikimedia Commons for the same type or operator.",
      tone: "soft",
    }
  );
});

test("getFreshnessMeta softens live age states", () => {
  assert.deepEqual(
    getFreshnessMeta({
      snapshotFreshness: "8s old",
      detailFreshness: "3s old",
      detailsStatus: "success",
      snapshotFeedLabel: "ADSB.lol",
      snapshotTransport: "Polling",
    }),
    {
      label: "Live",
      note: "Live frame 8s old, details 3s old.",
      tone: "strong",
    }
  );

  assert.deepEqual(
    getFreshnessMeta({
      snapshotFreshness: "144s old",
      detailFreshness: "23s old",
      detailsStatus: "success",
      snapshotFeedLabel: "ADSB.lol",
      snapshotTransport: "Polling",
    }),
    {
      label: "Cached",
      note: "Live frame 144s old, details 23s old.",
      tone: "muted",
    }
  );
});
