import L from "leaflet";

function formatAltitude(value) {
  if (value === null || value === undefined) {
    return "unknown";
  }

  return `${Math.round(value)} m`;
}

export function createAircraftIcon(track = 0) {
  return L.divIcon({
    className: "aircraft-icon-shell",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `
      <div class="aircraft-icon" style="transform: rotate(${track}deg);">
        <svg viewBox="0 0 48 48" width="30" height="30" aria-hidden="true">
          <path
            d="M24 3L29 20L43 24L29 28L24 45L19 28L5 24L19 20L24 3Z"
            fill="#12395d"
            stroke="#f2f8ff"
            stroke-width="2"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    `,
  });
}

export function syncAircraftMarkers(layer, registry, flights) {
  const nextIds = new Set();

  for (const flight of flights) {
    nextIds.add(flight.icao24);

    const latLng = [flight.latitude, flight.longitude];
    const tooltip = `
      <strong>${flight.callsign ?? "Unknown callsign"}</strong><br />
      ICAO24: ${flight.icao24}<br />
      Altitude: ${formatAltitude(flight.altitude)}
    `;

    const existingMarker = registry.get(flight.icao24);
    if (existingMarker) {
      existingMarker.setLatLng(latLng);
      existingMarker.setIcon(createAircraftIcon(flight.true_track ?? 0));
      existingMarker.bindPopup(tooltip);
      continue;
    }

    const marker = L.marker(latLng, {
      icon: createAircraftIcon(flight.true_track ?? 0),
      keyboard: false,
    }).bindPopup(tooltip);

    marker.addTo(layer);
    registry.set(flight.icao24, marker);
  }

  for (const [icao24, marker] of registry.entries()) {
    if (nextIds.has(icao24)) {
      continue;
    }

    layer.removeLayer(marker);
    registry.delete(icao24);
  }
}
