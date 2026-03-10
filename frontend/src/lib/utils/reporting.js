function escapeCsvValue(value) {
  const normalized = String(value ?? "");
  if (/[",\n]/.test(normalized)) {
    return `"${normalized.replace(/"/g, '""')}"`;
  }
  return normalized;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildCsv(columns, rows) {
  const header = columns.map((column) => escapeCsvValue(column.label)).join(",");
  const body = rows.map((row) =>
    columns.map((column) => escapeCsvValue(row[column.key] ?? "")).join(",")
  );

  return [header, ...body].join("\n");
}

export function buildTrafficReportCsv(flights) {
  return buildCsv(
    [
      { key: "callsign", label: "callsign" },
      { key: "icao24", label: "icao24" },
      { key: "registration", label: "registration" },
      { key: "type_code", label: "type_code" },
      { key: "operator_code", label: "operator_code" },
      { key: "airline_code", label: "airline_code" },
      { key: "route_label", label: "route_label" },
      { key: "origin", label: "origin" },
      { key: "destination", label: "destination" },
      { key: "altitude_m", label: "altitude_m" },
      { key: "speed_kmh", label: "speed_kmh" },
      { key: "status", label: "status" },
    ],
    (flights ?? []).map((flight) => ({
      callsign: flight?.callsign ?? "",
      icao24: flight?.icao24 ?? "",
      registration: flight?.registration ?? "",
      type_code: flight?.type_code ?? "",
      operator_code: flight?.operator_code ?? "",
      airline_code: flight?.airline_code ?? "",
      route_label: flight?.route_label ?? flight?.iata_codes ?? "",
      origin:
        flight?.origin ?? flight?.origin_iata ?? flight?.origin_icao ?? "",
      destination:
        flight?.destination ??
        flight?.destination_iata ??
        flight?.destination_icao ??
        "",
      altitude_m:
        flight?.altitude === null || flight?.altitude === undefined
          ? ""
          : Math.round(flight.altitude),
      speed_kmh:
        flight?.velocity === null || flight?.velocity === undefined
          ? ""
          : Math.round(flight.velocity * 3.6),
      status: flight?.on_ground ? "ground" : "airborne",
    }))
  );
}

export function buildAirportReportCsv(airport, dashboard) {
  const airportCode =
    airport?.iata ?? airport?.icao ?? airport?.entity_key ?? "AIRPORT";
  const recentArrivals = dashboard?.recent?.arrivals ?? [];
  const recentDepartures = dashboard?.recent?.departures ?? [];
  const nearbyFlights = dashboard?.live?.nearby ?? [];

  const rows = [
    ...recentArrivals.map((flight) => ({
      airport: airportCode,
      movement_type: "arrival",
      callsign: flight?.callsign ?? "",
      icao24: flight?.icao24 ?? "",
      registration: flight?.registration ?? "",
      route: `${flight?.origin ?? ""} -> ${flight?.destination ?? airportCode}`.trim(),
      altitude_m:
        flight?.altitude === null || flight?.altitude === undefined
          ? ""
          : Math.round(flight.altitude),
      speed_kmh:
        flight?.velocity === null || flight?.velocity === undefined
          ? ""
          : Math.round(flight.velocity * 3.6),
      fetched_at: flight?.fetched_at ?? "",
    })),
    ...recentDepartures.map((flight) => ({
      airport: airportCode,
      movement_type: "departure",
      callsign: flight?.callsign ?? "",
      icao24: flight?.icao24 ?? "",
      registration: flight?.registration ?? "",
      route: `${flight?.origin ?? airportCode} -> ${flight?.destination ?? ""}`.trim(),
      altitude_m:
        flight?.altitude === null || flight?.altitude === undefined
          ? ""
          : Math.round(flight.altitude),
      speed_kmh:
        flight?.velocity === null || flight?.velocity === undefined
          ? ""
          : Math.round(flight.velocity * 3.6),
      fetched_at: flight?.fetched_at ?? "",
    })),
    ...nearbyFlights.map((flight) => ({
      airport: airportCode,
      movement_type: flight?.on_ground ? "ground" : "nearby",
      callsign: flight?.callsign ?? "",
      icao24: flight?.icao24 ?? "",
      registration: flight?.registration ?? "",
      route: `${flight?.origin ?? ""} -> ${flight?.destination ?? ""}`.trim(),
      altitude_m:
        flight?.altitude === null || flight?.altitude === undefined
          ? ""
          : Math.round(flight.altitude),
      speed_kmh:
        flight?.velocity === null || flight?.velocity === undefined
          ? ""
          : Math.round(flight.velocity * 3.6),
      fetched_at: flight?.fetched_at ?? "",
    })),
  ];

  return buildCsv(
    [
      { key: "airport", label: "airport" },
      { key: "movement_type", label: "movement_type" },
      { key: "callsign", label: "callsign" },
      { key: "icao24", label: "icao24" },
      { key: "registration", label: "registration" },
      { key: "route", label: "route" },
      { key: "altitude_m", label: "altitude_m" },
      { key: "speed_kmh", label: "speed_kmh" },
      { key: "fetched_at", label: "fetched_at" },
    ],
    rows
  );
}

export function buildPrintableRadarReport({
  title,
  generatedAt,
  summaryRows = [],
  flights = [],
}) {
  const summaryMarkup = summaryRows
    .map(
      (row) => `
        <div class="summary-card">
          <span>${escapeHtml(row.label)}</span>
          <strong>${escapeHtml(row.value)}</strong>
        </div>
      `
    )
    .join("");

  const rowsMarkup = (flights ?? [])
    .map(
      (flight) => `
        <tr>
          <td>${escapeHtml(flight.callsign ?? flight.registration ?? flight.icao24 ?? "")}</td>
          <td>${escapeHtml(flight.route_label ?? flight.iata_codes ?? "")}</td>
          <td>${escapeHtml(flight.origin ?? flight.origin_country ?? "")}</td>
          <td>${escapeHtml(flight.destination ?? "")}</td>
          <td>${escapeHtml(
            flight.altitude === null || flight.altitude === undefined
              ? ""
              : String(Math.round(flight.altitude))
          )}</td>
          <td>${escapeHtml(
            flight.velocity === null || flight.velocity === undefined
              ? ""
              : String(Math.round(flight.velocity * 3.6))
          )}</td>
          <td>${escapeHtml(flight.on_ground ? "Ground" : "Airborne")}</td>
        </tr>
      `
    )
    .join("");

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${escapeHtml(title)}</title>
    <style>
      body {
        margin: 0;
        padding: 24px;
        font-family: "IBM Plex Sans", system-ui, sans-serif;
        color: #111827;
        background: #f3f4f6;
      }

      .report {
        max-width: 1100px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
      }

      .report-header h1,
      .report-header p {
        margin: 0;
      }

      .report-header p {
        margin-top: 8px;
        color: #4b5563;
      }

      .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-top: 20px;
      }

      .summary-card {
        padding: 14px;
        border-radius: 14px;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
      }

      .summary-card span {
        display: block;
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6b7280;
      }

      .summary-card strong {
        display: block;
        margin-top: 6px;
        font-size: 20px;
      }

      table {
        width: 100%;
        margin-top: 24px;
        border-collapse: collapse;
      }

      th,
      td {
        padding: 10px 12px;
        border-bottom: 1px solid #e5e7eb;
        text-align: left;
        font-size: 14px;
      }

      th {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
      }
    </style>
  </head>
  <body>
    <main class="report">
      <header class="report-header">
        <h1>${escapeHtml(title)}</h1>
        <p>Generated ${escapeHtml(generatedAt)}</p>
      </header>
      <section class="summary-grid">${summaryMarkup}</section>
      <table>
        <thead>
          <tr>
            <th>Flight</th>
            <th>Route</th>
            <th>Origin</th>
            <th>Destination</th>
            <th>Altitude m</th>
            <th>Speed km/h</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>${rowsMarkup}</tbody>
      </table>
    </main>
  </body>
</html>`;
}
