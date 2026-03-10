function normalizeOperatorValue(value) {
  return String(value ?? "").trim().toUpperCase();
}

export function deriveOperatorCode(flightOrCallsign) {
  if (flightOrCallsign && typeof flightOrCallsign === "object") {
    const explicitCode = normalizeOperatorValue(
      flightOrCallsign.operator_code ?? flightOrCallsign.airline_code
    );
    if (explicitCode) {
      return explicitCode;
    }
  }

  const rawCallsign =
    typeof flightOrCallsign === "string"
      ? flightOrCallsign
      : flightOrCallsign?.callsign ?? "";
  const normalizedCallsign = normalizeOperatorValue(rawCallsign);
  const match = normalizedCallsign.match(/^[A-Z]{3}/);
  return match ? match[0] : "";
}

export function getFlightSearchFields(flight) {
  return [
    flight?.icao24,
    flight?.callsign,
    flight?.registration,
    flight?.type_code,
    flight?.origin_country,
    flight?.operator_code,
    flight?.airline_code,
    flight?.flight_number,
    flight?.route_label,
    flight?.route_verbose,
    flight?.airport_codes,
    flight?.iata_codes,
    flight?.origin,
    flight?.destination,
    flight?.origin_iata,
    flight?.origin_icao,
    flight?.origin_name,
    flight?.destination_iata,
    flight?.destination_icao,
    flight?.destination_name,
  ]
    .filter(Boolean)
    .map((value) => String(value).toLowerCase());
}

export function matchesFlightSearch(flight, query) {
  const normalizedQuery = String(query ?? "").trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }

  return getFlightSearchFields(flight).some((value) => value.includes(normalizedQuery));
}

function getAirportFlowFields(flight, flow) {
  if (flow === "departures") {
    return [
      flight?.origin,
      flight?.origin_iata,
      flight?.origin_icao,
      flight?.origin_name,
    ];
  }

  if (flow === "arrivals") {
    return [
      flight?.destination,
      flight?.destination_iata,
      flight?.destination_icao,
      flight?.destination_name,
    ];
  }

  return [
    flight?.origin,
    flight?.origin_iata,
    flight?.origin_icao,
    flight?.origin_name,
    flight?.destination,
    flight?.destination_iata,
    flight?.destination_icao,
    flight?.destination_name,
  ];
}

export function matchesAirportTrafficFilter(flight, airportCode, airportFlow = "all") {
  const normalizedAirportCode = String(airportCode ?? "").trim().toLowerCase();
  if (!normalizedAirportCode) {
    return true;
  }

  return getAirportFlowFields(flight, airportFlow)
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(normalizedAirportCode));
}
