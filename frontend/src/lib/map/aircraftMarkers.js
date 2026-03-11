import L from "leaflet";

import {
  formatAltitude,
  formatFlightStatus,
  formatHeading,
  formatSpeed,
  formatVerticalRate,
} from "../utils/flightFormatters.js";
import { shouldUseDetailedAircraftMarker } from "../utils/mapPerformance.js";

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

function buildSelectedTooltipContent(flight) {
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

function bindMarkerTooltip(entry, selected) {
  if (!entry?.marker || entry.renderMode !== "detailed") {
    return;
  }

  const nextTooltipMode = selected ? "selected" : "hover";
  if (entry.tooltipMode !== nextTooltipMode) {
    entry.marker.unbindTooltip();
    entry.marker.bindTooltip(
      selected ? buildSelectedTooltipContent(entry.flight) : buildTooltipContent(entry.flight),
      selected
        ? {
            permanent: true,
            direction: "top",
            offset: [0, -24],
            opacity: 1,
            className: "aircraft-selected-tooltip",
          }
        : {
            direction: "top",
            offset: [0, -18],
            opacity: 1,
            className: "aircraft-hover-tooltip",
          }
    );
    entry.tooltipMode = nextTooltipMode;
    return;
  }

  entry.marker.setTooltipContent(
    selected ? buildSelectedTooltipContent(entry.flight) : buildTooltipContent(entry.flight)
  );
}

function syncMarkerOverlayState(entry, selected) {
  if (!entry?.marker || entry.renderMode !== "detailed") {
    return;
  }

  if (selected) {
    bindMarkerTooltip(entry, true);
    entry.marker.openTooltip();
    return;
  }

  if (entry.tooltipMode === "selected") {
    bindMarkerTooltip(entry, false);
  }

  entry.marker.closeTooltip();
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

function getVisualPalette(selected, watched, watchModeEnabled, dimmed) {
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

  return {
    fillColor,
    strokeColor,
    opacity,
  };
}

function setMarkerDataset(marker, icao24) {
  const markerElement = marker.getElement?.();
  if (markerElement) {
    markerElement.dataset.icao24 = icao24;
  }
}

function getDetailedVisualKey(track, selected, watched, watchModeEnabled, dimmed) {
  return [
    Math.round(track ?? 0),
    selected ? 1 : 0,
    watched ? 1 : 0,
    watchModeEnabled ? 1 : 0,
    dimmed ? 1 : 0,
  ].join(":");
}

function getLiteStyle(flight, selected, watched, watchModeEnabled, dimmed) {
  const { fillColor, strokeColor, opacity } = getVisualPalette(
    selected,
    watched,
    watchModeEnabled,
    dimmed
  );
  const airborne = !flight.on_ground;

  return {
    radius: selected ? 6 : watched ? 5 : airborne ? 3.6 : 3,
    weight: airborne ? 1 : 0.8,
    color: strokeColor,
    opacity: Math.min(0.9, opacity),
    fillColor,
    fillOpacity: airborne ? Math.max(0.58, opacity * 0.86) : Math.max(0.42, opacity * 0.74),
  };
}

function getLiteVisualKey(flight, selected, watched, watchModeEnabled, dimmed) {
  return [
    selected ? 1 : 0,
    watched ? 1 : 0,
    watchModeEnabled ? 1 : 0,
    dimmed ? 1 : 0,
    flight.on_ground ? 1 : 0,
  ].join(":");
}

export function createAircraftIcon(
  track = 0,
  selected = false,
  watched = false,
  watchModeEnabled = false,
  dimmed = false
) {
  const { fillColor, strokeColor, opacity } = getVisualPalette(
    selected,
    watched,
    watchModeEnabled,
    dimmed
  );
  const shellClassNames = [
    "aircraft-icon-shell",
    selected ? "is-selected" : "",
    watched ? "is-watched" : "",
    dimmed ? "is-dimmed" : "",
    watchModeEnabled && !watched && !selected ? "is-muted" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return L.divIcon({
    className: shellClassNames,
    iconSize: [28, 30],
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
      </div>
    `,
  });
}

function createDetailedMarkerEntry(
  layer,
  flight,
  selected,
  watched,
  watchModeEnabled,
  dimmed,
  onSelect
) {
  const marker = L.marker([flight.latitude, flight.longitude], {
    interactive: true,
    bubblingMouseEvents: false,
    riseOnHover: true,
    icon: createAircraftIcon(
      flight.true_track ?? 0,
      selected,
      watched,
      watchModeEnabled,
      dimmed
    ),
    keyboard: false,
  });

  const entry = {
    marker,
    flight,
    selected,
    tooltipMode: null,
    animationFrame: null,
    renderMode: "detailed",
    visualKey: getDetailedVisualKey(
      flight.true_track ?? 0,
      selected,
      watched,
      watchModeEnabled,
      dimmed
    ),
  };

  marker.on("mouseover", () => {
    if (entry.selected) {
      return;
    }

    bindMarkerTooltip(entry, false);
    marker.openTooltip();
  });

  marker.on("mouseout", () => {
    if (entry.selected) {
      return;
    }

    marker.closeTooltip();
  });

  marker.on("click", (event) => {
    L.DomEvent.stop(event.originalEvent ?? event);
    if (onSelect) {
      onSelect(entry.flight);
    }
  });

  marker.setZIndexOffset(selected ? 1200 : watched ? 480 : 0);
  marker.addTo(layer);
  setMarkerDataset(marker, flight.icao24);
  syncMarkerOverlayState(entry, selected);
  return entry;
}

function createLiteMarkerEntry(layer, flight, selected, watched, watchModeEnabled, dimmed) {
  const marker = L.circleMarker([flight.latitude, flight.longitude], {
    ...getLiteStyle(flight, selected, watched, watchModeEnabled, dimmed),
    bubblingMouseEvents: false,
    interactive: false,
    keyboard: false,
  }).addTo(layer);

  return {
    marker,
    flight,
    selected,
    tooltipMode: null,
    animationFrame: null,
    renderMode: "lite",
    visualKey: getLiteVisualKey(flight, selected, watched, watchModeEnabled, dimmed),
  };
}

function createMarkerEntry(
  layer,
  flight,
  selectedIcao24,
  watchedIcao24s,
  watchModeEnabled,
  dimmedIcao24s,
  onSelect,
  renderMode
) {
  const selected = selectedIcao24 === flight.icao24;
  const watched = watchedIcao24s.has(flight.icao24);
  const dimmed = dimmedIcao24s.has(flight.icao24);
  const detailedMarker = shouldUseDetailedAircraftMarker(renderMode, selected, watched);

  if (detailedMarker) {
    return createDetailedMarkerEntry(
      layer,
      flight,
      selected,
      watched,
      watchModeEnabled,
      dimmed,
      onSelect
    );
  }

  return createLiteMarkerEntry(layer, flight, selected, watched, watchModeEnabled, dimmed);
}

function removeMarkerEntry(layer, entry) {
  if (entry.animationFrame) {
    cancelAnimationFrame(entry.animationFrame);
  }

  layer.removeLayer(entry.marker);
}

function replaceMarkerEntry(
  layer,
  entry,
  flight,
  selected,
  watched,
  watchModeEnabled,
  dimmed,
  onSelect,
  renderMode
) {
  removeMarkerEntry(layer, entry);

  return createMarkerEntry(
    layer,
    flight,
    selected ? flight.icao24 : null,
    watched ? new Set([flight.icao24]) : new Set(),
    watchModeEnabled,
    dimmed ? new Set([flight.icao24]) : new Set(),
    onSelect,
    renderMode
  );
}

function updateDetailedMarkerEntry(entry, flight, selected, watched, watchModeEnabled, dimmed) {
  const nextLatLng = [flight.latitude, flight.longitude];
  const previousSelected = entry.selected;
  const visualKey = getDetailedVisualKey(
    flight.true_track ?? 0,
    selected,
    watched,
    watchModeEnabled,
    dimmed
  );

  entry.flight = flight;
  entry.selected = selected;

  if (entry.visualKey !== visualKey) {
    entry.marker.setIcon(
      createAircraftIcon(
        flight.true_track ?? 0,
        selected,
        watched,
        watchModeEnabled,
        dimmed
      )
    );
    entry.visualKey = visualKey;
  }

  animateMarkerPosition(entry, nextLatLng);
  entry.marker.setZIndexOffset(selected ? 1200 : watched ? 480 : 0);
  setMarkerDataset(entry.marker, flight.icao24);

  if (selected || previousSelected !== selected) {
    syncMarkerOverlayState(entry, selected);
    return;
  }

  if (entry.tooltipMode === "hover" && entry.marker.isTooltipOpen()) {
    bindMarkerTooltip(entry, false);
  }
}

function updateLiteMarkerEntry(entry, flight, selected, watched, watchModeEnabled, dimmed) {
  const nextLatLng = [flight.latitude, flight.longitude];
  const visualKey = getLiteVisualKey(flight, selected, watched, watchModeEnabled, dimmed);

  entry.flight = flight;
  entry.selected = selected;

  if (entry.animationFrame) {
    cancelAnimationFrame(entry.animationFrame);
    entry.animationFrame = null;
  }

  entry.marker.setLatLng(nextLatLng);

  if (entry.visualKey !== visualKey) {
    entry.marker.setStyle(getLiteStyle(flight, selected, watched, watchModeEnabled, dimmed));
    entry.visualKey = visualKey;
  }
}

function updateMarkerEntry(
  layer,
  entry,
  flight,
  selected,
  watched,
  watchModeEnabled,
  dimmed,
  onSelect,
  renderMode
) {
  const nextDetailedState = shouldUseDetailedAircraftMarker(renderMode, selected, watched);

  if (entry.renderMode !== (nextDetailedState ? "detailed" : "lite")) {
    return replaceMarkerEntry(
      layer,
      entry,
      flight,
      selected,
      watched,
      watchModeEnabled,
      dimmed,
      onSelect,
      renderMode
    );
  }

  if (nextDetailedState) {
    updateDetailedMarkerEntry(entry, flight, selected, watched, watchModeEnabled, dimmed);
    return entry;
  }

  updateLiteMarkerEntry(entry, flight, selected, watched, watchModeEnabled, dimmed);
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
  onSelect,
  renderMode = "detailed"
) {
  const nextIds = new Set();

  for (const flight of flights) {
    nextIds.add(flight.icao24);

    const selected = selectedIcao24 === flight.icao24;
    const watched = watchedIcao24s.has(flight.icao24);
    const dimmed = dimmedIcao24s.has(flight.icao24);
    const existingEntry = registry.get(flight.icao24);

    if (existingEntry) {
      const nextEntry = updateMarkerEntry(
        layer,
        existingEntry,
        flight,
        selected,
        watched,
        watchModeEnabled,
        dimmed,
        onSelect,
        renderMode
      );
      registry.set(flight.icao24, nextEntry);
      continue;
    }

    const entry = createMarkerEntry(
      layer,
      flight,
      selectedIcao24,
      watchedIcao24s,
      watchModeEnabled,
      dimmedIcao24s,
      onSelect,
      renderMode
    );
    registry.set(flight.icao24, entry);
  }

  for (const [icao24, entry] of registry.entries()) {
    if (nextIds.has(icao24)) {
      continue;
    }

    removeMarkerEntry(layer, entry);
    registry.delete(icao24);
  }
}
