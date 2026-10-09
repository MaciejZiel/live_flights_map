import test from "node:test";
import assert from "node:assert/strict";

import { buildProviderStatus, formatCooldownDuration } from "../src/lib/utils/providerStatus.js";

test("formats cooldown durations into compact labels", () => {
  assert.equal(formatCooldownDuration(18), "18s");
  assert.equal(formatCooldownDuration(61), "2m");
  assert.equal(formatCooldownDuration(80138), "22h 16m");
  assert.equal(formatCooldownDuration(0), null);
});

test("builds a source summary with global, regional and remaining cooldown status", () => {
  const status = buildProviderStatus(
    {
      provider_used: "opensky",
      providers_configured: ["opensky", "adsb_lol"],
      provider_cooldowns: { opensky: 120 },
      provider_cooldowns_observed_at: { opensky: 1_000 },
      regional_supplement_count: 32,
      regional_supplement_tiles: 1,
    },
    31_000
  );

  assert.equal(status.globalSource, "OpenSky");
  assert.equal(status.regionalSource, "ADSB.lol +32 local");
  assert.equal(status.compactRegional, "Local +32 · OpenSky ~2m");
  assert.deepEqual(status.cooldowns, ["OpenSky retry ~2m"]);
  assert.match(status.summary, /OpenSky · ADSB\.lol \+32 local · OpenSky retry ~2m/);
});

test("drops cooldowns that have elapsed and explains local zoom coverage", () => {
  const status = buildProviderStatus(
    {
      providers_configured: ["opensky", "adsb_lol"],
      provider_cooldowns: { opensky: 30 },
      provider_cooldowns_observed_at: { opensky: 1_000 },
    },
    32_000
  );

  assert.deepEqual(status.cooldowns, []);
  assert.equal(status.regionalSource, "ADSB.lol at zoom 6+");
  assert.equal(status.compactRegional, "Local ADS-B at zoom 6+");
});

test("labels synthetic demo traffic instead of live providers", () => {
  const status = buildProviderStatus({
    provider_used: "demo",
    providers_configured: ["demo"],
    demo: { synthetic: true },
  });

  assert.equal(status.globalSource, "Synthetic demo");
  assert.equal(status.regionalSource, "Synthetic, no regional lookups");
  assert.doesNotMatch(status.summary, /ADSB\.lol/);
});
