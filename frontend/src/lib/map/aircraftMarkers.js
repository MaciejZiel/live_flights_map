import L from "leaflet";

import {
  formatAltitude,
  formatFlightStatus,
  formatHeading,
  formatSpeed,
  formatVerticalRate,
} from "../utils/flightFormatters.js";

const POSITION_ANIMATION_MS = 1400;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getMarkerLabel(flight) {
  return flight.callsign ?? flight.registration ?? flight.icao24?.toUpperCase() ?? "Unknown";
}

function buildTooltipContent(flight) {
  return `
    <div class="aircraft-hover-card">
      <strong>${escapeHtml(getMarkerLabel(flight))}</strong>
      <span>${escapeHtml(flight.registration ?? flight.icao24?.toUpperCase() ?? "Unknown")}</span>
      <small>${escapeHtml(flight.origin_country ?? "Unknown")} · ${escapeHtml(formatFlightStatus(flight))}</small>
      <div class="aircraft-hover-metrics">
        <span>${escapeHtml(formatAltitude(flight.altitude))}</span>
        <span>${escapeHtml(formatSpeed(flight.velocity))}</span>
        <span>${escapeHtml(formatHeading(flight.true_track))}</span>
      </div>
    </div>
  `;
}

function buildPopupContent(flight) {
  return `
    <div class="aircraft-popup-card">
      <div class="aircraft-popup-head">
        <strong>${escapeHtml(getMarkerLabel(flight))}</strong>
        <span>${escapeHtml(formatFlightStatus(flight))}</span>
      </div>
      <div class="aircraft-popup-meta">
        <span>${escapeHtml(flight.registration ?? flight.icao24?.toUpperCase() ?? "Unknown")}</span>
        <span>${escapeHtml(flight.origin_country ?? "Unknown")}</span>
      </div>
      <div class="aircraft-popup-grid">
        <div>
          <small>ALT</small>
          <strong>${escapeHtml(formatAltitude(flight.altitude))}</strong>
        </div>
        <div>
          <small>SPD</small>
          <strong>${escapeHtml(formatSpeed(flight.velocity))}</strong>
        </div>
        <div>
          <small>HDG</small>
          <strong>${escapeHtml(formatHeading(flight.true_track))}</strong>
        </div>
        <div>
          <small>V/S</small>
          <strong>${escapeHtml(formatVerticalRate(flight.vertical_rate))}</strong>
        </div>
      </div>
    </div>
  `;
}

function easeOutCubic(progress) {
  return 1 - (1 - progress) ** 3;
}

function animateMarkerPosition(entry, nextLatLng) {
  const startLatLng = entry.marker.getLatLng();
  const startedAt = performance.now();

  if (entry.animationFrame) {
    cancelAnimationFrame(entry.animationFrame);
  }

  const step = (timestamp) => {
    const progress = Math.min((timestamp - startedAt) / POSITION_ANIMATION_MS, 1);
    const eased = easeOutCubic(progress);
    const latitude = startLatLng.lat + (nextLatLng[0] - startLatLng.lat) * eased;
    const longitude = startLatLng.lng + (nextLatLng[1] - startLatLng.lng) * eased;

    entry.marker.setLatLng([latitude, longitude]);

    if (progress < 1) {
      entry.animationFrame = requestAnimationFrame(step);
      return;
    }

    entry.animationFrame = null;
  };

  entry.animationFrame = requestAnimationFrame(step);
}

export function createAircraftIcon(
  track = 0,
  selected = false,
  watched = false,
  watchModeEnabled = false,
  label = null,
  dimmed = false
) {
  const fillColor = selected
    ? "#86d2ff"
    : watched
      ? "#7df0b1"
      : dimmed
        ? "#8893a0"
        : watchModeEnabled
          ? "#9aa5b3"
          : "#f7c716";
  const strokeColor = selected ? "#eff9ff" : watched ? "#ecfff4" : dimmed ? "#3d4650" : "#46370a";
  const opacity = dimmed ? 0.32 : watchModeEnabled && !watched && !selected ? 0.45 : 1;
  const shellClassNames = [
    "aircraft-icon-shell",
    selected ? "is-selected" : "",
    watched ? "is-watched" : "",
    dimmed ? "is-dimmed" : "",
    watchModeEnabled && !watched && !selected ? "is-muted" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const resolvedLabel = label ? escapeHtml(label) : "";
  const iconWidth = selected ? Math.min(176, Math.max(88, resolvedLabel.length * 8 + 42)) : 28;

  return L.divIcon({
    className: shellClassNames,
    iconSize: [iconWidth, 30],
    iconAnchor: [14, 14],
    html: `
      <div class="aircraft-marker">
        <div class="aircraft-icon-wrap" style="opacity: ${opacity};">
          <svg class="aircraft-icon" viewBox="0 0 48 48" width="22" height="22" aria-hidden="true" style="transform: rotate(${track}deg);">
            <path
              d="M22 3h4l3 12 11 7v4l-11-2.5 1.8 8.2 4.7 4v3.3L26 36.7V45h-4v-8.3l-9.5 2.3v-3.3l4.7-4 1.8-8.2L8 26v-4l11-7 3-12Z"
              fill="${fillColor}"
              stroke="${strokeColor}"
              stroke-width="1.7"
              stroke-linejoin="round"
            />
          </svg>
        </div>
        ${selected ? `<span class="aircraft-callout">${resolvedLabel}</span>` : ""}
      </div>
    `,
  });
}

function updateMarkerEntry(entry, flight, selected, watched, watchModeEnabled, dimmed) {
  const nextLatLng = [flight.latitude, flight.longitude];

  entry.flight = flight;
  animateMarkerPosition(entry, nextLatLng);
  entry.marker.setIcon(
    createAircraftIcon(
      flight.true_track ?? 0,
      selected,
      watched,
      watchModeEnabled,
      selected ? getMarkerLabel(flight) : null,
      dimmed
    )
  );
  entry.marker.setTooltipContent(buildTooltipContent(flight));
  entry.marker.setPopupContent(buildPopupContent(flight));
  entry.marker.setZIndexOffset(selected ? 1200 : watched ? 480 : 0);

  const markerElement = entry.marker.getElement();
  if (markerElement) {
    markerElement.dataset.icao24 = flight.icao24;
  }
}

function createMarkerEntry(
  layer,
  flight,
  selectedIcao24,
  watchedIcao24s,
  watchModeEnabled,
  dimmedIcao24s,
  onSelect
) {
  const marker = L.marker([flight.latitude, flight.longitude], {
    interactive: true,
    bubblingMouseEvents: false,
    riseOnHover: true,
    icon: createAircraftIcon(
      flight.true_track ?? 0,
      selectedIcao24 === flight.icao24,
      watchedIcao24s.has(flight.icao24),
      watchModeEnabled,
      selectedIcao24 === flight.icao24 ? getMarkerLabel(flight) : null,
      dimmedIcao24s.has(flight.icao24)
    ),
    keyboard: false,
  }).bindTooltip(buildTooltipContent(flight), {
    direction: "top",
    offset: [0, -18],
    opacity: 1,
    className: "aircraft-hover-tooltip",
  }).bindPopup(buildPopupContent(flight), {
    autoPan: true,
    autoClose: false,
    closeButton: false,
    className: "aircraft-stats-popup",
    offset: [0, -16],
  });

  const entry = {
    marker,
    flight,
    animationFrame: null,
  };

  marker.on("mouseover", () => {
    marker.openTooltip();
  });

  marker.on("mouseout", () => {
    marker.closeTooltip();
  });

  marker.on("click", (event) => {
    L.DomEvent.stop(event.originalEvent ?? event);
    marker.openPopup();
    if (onSelect) {
      onSelect(entry.flight);
    }
  });

  marker.setZIndexOffset(
    selectedIcao24 === flight.icao24 ? 1200 : watchedIcao24s.has(flight.icao24) ? 480 : 0
  );

  marker.addTo(layer);
  const markerElement = marker.getElement();
  if (markerElement) {
    markerElement.dataset.icao24 = flight.icao24;
  }
  return entry;
}

export function syncAircraftMarkers(
  layer,
  registry,
  flights,
  selectedIcao24,
  watchedIcao24s = new Set(),
  watchModeEnabled = false,
  dimmedIcao24s = new Set(),
  onSelect
) {
  const nextIds = new Set();

  for (const flight of flights) {
    nextIds.add(flight.icao24);

    const existingEntry = registry.get(flight.icao24);
    if (existingEntry) {
      updateMarkerEntry(
        existingEntry,
        flight,
        selectedIcao24 === flight.icao24,
        watchedIcao24s.has(flight.icao24),
        watchModeEnabled,
        dimmedIcao24s.has(flight.icao24)
      );
      continue;
    }

    const entry = createMarkerEntry(
      layer,
      flight,
      selectedIcao24,
      watchedIcao24s,
      watchModeEnabled,
      dimmedIcao24s,
      onSelect
    );
    registry.set(flight.icao24, entry);
  }

  for (const [icao24, entry] of registry.entries()) {
    if (nextIds.has(icao24)) {
      continue;
    }

    if (entry.animationFrame) {
      cancelAnimationFrame(entry.animationFrame);
    }

    layer.removeLayer(entry.marker);
    registry.delete(icao24);
  }
}
