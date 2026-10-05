# Product and feature inventory

This file describes implemented behavior in the repository. Provider coverage, enrichment and freshness depend on external aviation data sources.

## Live traffic map

- Polling by default, with an optional server-sent event transport and a local snapshot fallback.
- OpenSky and ADSB.lol provider chain, bounding-box aware queries, rate-limit cooldowns and provider diagnostics.
- Aircraft selection, marker clustering, density-aware Canvas/WebGL rendering, map style presets, airport markers and optional weather overlay.
- Filters for aircraft identity, altitude, speed, aircraft type, operator, route, traffic category, movement and activity.

## Flight discovery and inspection

- Scoped search for callsign, ICAO24, registration, airport, airline, route and named location.
- Aircraft details with best-effort identity, route and image enrichment, plus data-quality and freshness indicators.
- Position trail, estimated movement vector, flight selection history, watchlist, notes and map follow mode.
- Airport search and dashboards with nearby/live traffic, archived movements, weather, reports and CSV export.

## History and monitoring

- SQLite snapshots, latest-position cache, per-aircraft trail, recent-traffic search and time-window replay.
- Replay timeline with playback speed, timestamp selection and snapshot comparison.
- Browser alerts for matching traffic and transitions; optional server-side sweeper persists profile alert state.
- CSV and printable reports, saved views, share URLs and embeddable map links.

## Local workspaces

- Local workspace accounts and profiles persist map settings, filters, alert rules, notes, saved views and watchlists.
- The profile role field is descriptive demo state only. There is no authentication or server-side authorization; do not use it as a security boundary.

## Runtime and reliability

- Flask API, Svelte frontend, SQLite persistence and Docker Compose local setup.
- API diagnostics cover provider cooldowns, archive freshness, collector status and workspace/photo caches.
- Collector and alert workers are optional because they make additional live-provider requests. Archive retention maintenance runs separately.
- GitHub Actions checks backend tests, frontend unit tests, production build and a mocked Playwright browser flow.

## Data limitations

- ADS-B coverage depends on receivers, provider availability and rate limits. Global traffic views can be incomplete.
- Route, identity, photo, weather and airport movement details are best-effort enrichment and may be absent or stale.
- Replay only contains positions archived while a collector or a user-facing live request was active; it is not a complete historical flight database.
- Live position data is observational and should not be used for operational navigation or safety decisions.
