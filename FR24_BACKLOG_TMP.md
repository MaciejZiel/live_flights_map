**Full List**
This is the full list of items that should be treated as the backlog for bringing this application as close as possible to `FR24 1:1`. Nothing from the earlier direction is omitted here.

**1. Things that are currently too large / too loud and need to be simplified**
- Too many panels and overlays at the same time: topbar, ribbon, status strip, quick card, left panel, right panel, bottom dock.
- Too many features compete for attention instead of guiding the user through one primary workflow.
- `Guide` is overexposed.
- `Workspace` is overexposed.
- `Notes` are overexposed.
- `Comparison` is overexposed.
- `Monitoring sessions` are overexposed.
- `Saved views` are overexposed.
- Too much state and too many features still live only in the browser instead of feeling like a product system.
- The UI still feels too much like "our app" and not enough like "FR24".

**2. Things that are missing or still too thin**
- Search is not yet the true center of the application.
- Search must support: `flight`, `callsign`, `icao24`, `registration`, `aircraft type`, `airline`, `route`, `airport`, `location`.
- Search must return results grouped by entity type.
- Search must provide fast suggestions and a clear post-selection workflow.
- The full airport workflow is still missing.
- Airport pins are missing.
- The airport details panel is missing.
- `Arrivals` are missing.
- `Departures` are missing.
- Ground traffic / on-ground view is missing.
- Airport history is missing.
- Airport weather data is missing.
- Map layers closer to FR24 are missing.
- Weather layers are missing.
- More aviation-specific chart-like overlays are missing.
- Boundaries / operational overlays are missing when they make sense for the product.
- A more complete filtering system is missing.
- Full traffic categories are missing: `Passenger`, `Cargo`, `Business`, `Military`, `Helicopter`, `Government`, `Glider`, `Light aircraft`.
- A better dimming mode for aircraft outside active filters is missing.
- A fuller bookmarking system is missing.
- Bookmarks for `aircraft` are missing.
- Bookmarks for `flights` are missing.
- Bookmarks for `airports` are missing.
- Bookmarks for `locations` are missing.
- User accounts are missing.
- Preference and bookmark sync across sessions is missing.
- A fuller alerting system is missing.
- Product-level flight history is missing; only the local archive exists.
- Replay / playback is still too limited.

**3. Things that already exist but are not yet working ideally**
- The selected flight panel is still not as dominant and readable as FR24.
- Search does not yet guide the user as confidently as FR24 after a result is selected.
- Replay exists, but it is still shallow.
- Filters exist, but they are not yet at FR24 level.
- The global board exists, but it still needs visual and workflow polish.
- The quick card exists, but it must be checked against the main inspector to make sure it is not too loud.
- Mobile is better than before, but it still does not feel as smooth as desktop.
- The full application shell still needs more simplification and hierarchy.
- Selecting an aircraft and opening details is better, but still not `1:1 FR24`.
- The overall visual language is still not close enough to FR24.

**4. Main UI/UX work that still matters**
- Simplify the entire application shell.
- Keep the map as the absolute center.
- Make search the primary entry point for interaction.
- Make aircraft selection the primary workflow.
- Make the right inspector the main place to work with a flight.
- Reduce the number of equally visible sections on screen at the same time.
- Reduce visual noise.
- Improve information hierarchy.
- Improve spacing.
- Improve typography.
- Improve contrast.
- Improve hover / selected / active / disabled states.
- Unify the visual language across the whole app.
- Refine animations and transitions so they feel meaningful instead of decorative.
- Refine mobile drawers and mobile navigation.
- Bring the UI to a clean, ordered, easy-to-scan state.

**5. Search and result workflow**
- Rebuild search around an entity model instead of simple flight results only.
- Add results for flights.
- Add results for aircraft.
- Add results for registrations.
- Add results for airlines.
- Add results for airports.
- Add results for routes.
- Add results for locations.
- Group the results.
- Add clear result-type icons.
- Add secondary metadata inside results.
- Add strong keyboard-first opening of results.
- Clicking a flight result must: focus the map + open the inspector + show trail + show details.
- Clicking an airport result must: focus the map + open the airport panel.
- Clicking a location result must: focus the map on the saved area.
- Clicking an aircraft result must: focus the map + open the aircraft/flight panel.
- Add a sensible empty state.
- Add a sensible loading state.
- Add sensible search error handling.

**6. Flight panel / aircraft inspector**
- Make the right panel closer to FR24.
- Show the callsign as the main header.
- Show the route as the key context.
- Show registration.
- Show aircraft type.
- Show airline / operator.
- Show origin.
- Show destination.
- Show altitude.
- Show speed.
- Show heading.
- Show squawk when available.
- Show vertical speed when available.
- Show source / confidence / freshness.
- Show the trail.
- Show flight status and data quality.
- Add quick actions: `follow`, `bookmark`, `share`, `replay`, `alert`.
- Add a clearer card / section layout.
- Reduce secondary elements that are currently distracting.

**7. Airport workflow**
- Add airport as a first-class entity in the app model.
- Add airport pins.
- Add airport click support on the map.
- Add an airport panel.
- Add the `Arrivals` tab.
- Add the `Departures` tab.
- Add basic airport statistics.
- Add airport weather when the data source allows it.
- Add flight-to-airport linking.
- Add airport search results.
- Add airport bookmarks.
- Add airport share links.

**8. Replay / playback / history**
- Expand replay to a level closer to FR24.
- Add time and range selection.
- Add a better timeline feel.
- Add single-flight playback.
- Add global playback.
- Add a clear `Live` / `Replay` switch.
- Add better time labeling for data age.
- Add historical flight trails.
- Add history for a specific aircraft.
- Add history for a specific flight.
- Add history for a specific airport.
- Add better backend persistence for snapshots, tracks, and search indexes.

**9. Filters**
- Add a fuller set of flight-type and aircraft-type filters.
- Add airline filters.
- Add aircraft type filters.
- Add altitude filters.
- Add speed filters.
- Add status filters.
- Add region filters.
- Add better active filter tokens.
- Add dimming for aircraft that do not match the current filters instead of brutally hiding them when that improves UX.
- Add filter presets closer to FR24.

**10. Most tracked / global board**
- `Most tracked flights` must always be global, independent of the current bbox and map view.
- It must stay continuously visible.
- It must allow entering any flight from anywhere in the world.
- Clicking a flight from the board must focus the map on that flight and open details.
- The ranking must be credible and refreshed sensibly.
- It still needs more visual polish.

**11. Map interaction**
- Further refine markers.
- Further refine selected state.
- Further refine hover behavior.
- Further refine tooltips.
- Further refine clustering.
- Further refine behavior after clicking an aircraft.
- Further refine behavior after clicking empty map.
- Further refine map focus on the selected flight.
- Add map controls with a stronger FR24 feel.
- Add map layers closer to FR24.
- Make map switching feel less like a blank-screen transition.

**12. Bookmarks / watchlist / accounts**
- Expand bookmarks.
- Expand the watchlist.
- Connect both to user accounts.
- Add backend persistence.
- Add cross-session synchronization.
- Add a clear workflow for managing observed flights.
- Add support for flights, aircraft, airports, and locations.

**13. Alerts / monitoring**
- Add alerts for a specific flight.
- Add alerts for a specific aircraft.
- Add alerts for an airport.
- Add alerts for entering an area.
- Add alerts for takeoff / landing.
- Add alerts for altitude / speed / route when that makes sense and is supported by the data.
- Move alerts from a "local feature" into a real product workflow.

**14. Backend / data / quality**
- Clean up the data pipeline.
- Split `collector`, `normalizer`, `archive`, `api`, and `alerts worker` further if the repo grows.
- Improve global provider cooldown behavior.
- Improve cache policy.
- Improve durable flight archive storage.
- Improve data indexing for search.
- Expand the data model for airport, airline, route, and aircraft profile.
- Expand flight details.
- Improve resilience to provider failures.
- Improve fallback quality.
- Add stronger health checks and diagnostics.
- Add better error logging.
- Add better rate-limit handling.
- Add better data sources if we want to genuinely approach FR24 data quality.

**15. Constraint that must not be ignored**
- UI and workflow can be brought very close to FR24.
- Honest `1:1` data quality cannot be promised from public feeds alone.
- Reaching FR24-level data quality requires better feeds, deeper history, stronger enrichment, and stronger infrastructure.

**16. Delivery order that should be followed**
1. Simplify the shell and hide non-core features.
2. Rebuild `search + result workflow` toward an FR24 model.
3. Refine the right `flight inspector`.
4. Add the full `airport workflow`.
5. Expand `replay / playback / history`.
6. Expand filters and map layers.
7. Expand bookmarks, watchlist, and alerts.
8. Only after that, continue polishing secondary features.

If needed, this can be rewritten again as a hard `TODO` backlog, item by item, with no extra explanation.
