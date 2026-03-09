# Live Flights Map Feature Backlog

## Map and Movement

- Additional layers: country borders, FIRs, airports, ATS routes.
- Traffic heatmap for the selected region.
- Aircraft trail for the last few minutes.
- Predicted heading and motion vector.

## Aircraft Details

- Callsign, ICAO24, registration, aircraft type, operator, origin country.
- Origin and destination airports when available.
- Estimated arrival time.
- Position and altitude history for a selected flight.
- Aircraft or airline image where available.
- Flight category: passenger, cargo, private, military, medical.
- Dedicated full flight details view.

## Search and Filtering

- Search by callsign, ICAO24, registration, airline, aircraft type.
- Filters for altitude, speed, heading, country, operator.
- `Arrivals/departures for selected airport` filter.
- Traffic type filter: passenger, cargo, private, helicopter.
- Filter by recent activity window.
- Saved filter presets.
- Sorting by altitude, distance, speed, update time.

## Airports and Routes

- Clickable airports with arrivals and departures board.
- Nearby airports for a selected aircraft.
- Origin-to-destination route line.
- Active approach and departure view for airports.
- Live airport traffic statistics.
- Runway layout, approach zones, and holding pattern overlays.

## Alerts and Monitoring

- Alert when a selected aircraft enters a chosen area.
- Alert when an aircraft changes altitude, heading, or disappears.
- Alert for a specific callsign or registration.
- Airport alerts for arrival, departure, delay, or cancellation.
- Push, email, or webhook notifications.
- Watchlist for tracked aircraft and flights.
- Multi-aircraft watch mode.
- Geofencing with custom drawn areas.

## History and Analytics

- Historical replay on a timeline.
- Rewind and replay controls.
- Charts for altitude, speed, and vertical rate.
- Regional traffic stats: flight count, average altitude, popular routes.
- Day-over-day and week-over-week traffic comparison.
- Export flight history to CSV or JSON.
- Saved and replayable monitoring sessions.

## UX and Accessibility

- Collapsible and reorderable side panels.
- Responsive mobile layout with simplified map mode.
- Light and dark themes.
- Keyboard shortcuts.
- Tooltips and onboarding for new users.
- Multi-language interface.
- Clear `live`, `cached`, `error`, and `rate limited` states.
- Favorites for airports and aircraft.

## Data Quality and Performance

- Debounce and throttling on map moves.
- WebSocket or SSE updates instead of polling only.
- Progressive loading based on zoom level.
- Unified retry and error-handling policy.
- Performance monitoring and error logging.
- Automated backend and frontend tests.
- Support for multiple data providers, not only OpenSky.
- Data freshness and confidence indicators.

## Pro and Collaboration Features

- Side-by-side comparison for multiple flights.
- Custom dashboards and saved views.
- Public or private user API.
- Shareable link to a specific aircraft or map state.
- Embeddable map widget.
- PDF and CSV reports.
- User roles: viewer, analyst, admin.
- Alert history and audit trail.
- Integrations with Discord, Slack, and Telegram.
- Notes, comments, and tags for flights.

## Suggested Delivery Order

### Must Have

- Advanced search and filtering.
- Aircraft details view with trail history.
- Watchlist and alerting basics.
- History and replay foundation.
- Better realtime transport such as WebSocket or SSE.

### Should Have

- Airport views and route overlays.
- Saved presets and saved dashboards.
- Data quality indicators and richer caching logic.
- Mobile UX and theme support.
- Export and reporting.

### Nice to Have

- Multi-provider support.
- Collaboration features and notes.
- Embeddable widgets and public sharing.
- Role-based access.
- Premium analytics and comparisons.
