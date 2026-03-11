import { deriveOperatorCode } from "./flightMatching.js";

export const ALERT_RULE_OPTIONS = [
  { value: "callsign", label: "Callsign", placeholder: "LOT285" },
  { value: "icao24", label: "ICAO24", placeholder: "48ad08" },
  { value: "airline", label: "Airline", placeholder: "LOT" },
  { value: "country", label: "Country", placeholder: "Poland" },
  { value: "registration", label: "Registration", placeholder: "SP-LVQ" },
  { value: "type_code", label: "Aircraft type", placeholder: "B38M" },
  { value: "route", label: "Route", placeholder: "WAW-JFK" },
  { value: "altitude_min", label: "Min altitude", placeholder: "12000" },
  { value: "speed_min", label: "Min speed", placeholder: "850" },
  { value: "takeoff", label: "Takeoff", placeholder: "Visible traffic", queryOptional: true },
  { value: "landing", label: "Landing", placeholder: "Visible traffic", queryOptional: true },
];

export const ALERT_SEVERITY_OPTIONS = [
  { value: "info", label: "Info" },
  { value: "important", label: "Important" },
  { value: "critical", label: "Critical" },
];

const ALERT_RULE_LABELS = {
  callsign: "Callsign",
  icao24: "ICAO24",
  airline: "Airline",
  country: "Country",
  registration: "Registration",
  type_code: "Type",
  route: "Route",
  airport: "Airport",
  area: "Area",
  altitude_min: "Altitude",
  speed_min: "Speed",
  takeoff: "Takeoff",
  landing: "Landing",
};

const DEFAULT_TRANSITION_QUERY = "Visible traffic";
const DEFAULT_ALERT_COOLDOWN_MINUTES = 10;
const DEFAULT_ALERT_SEVERITY = {
  callsign: "important",
  icao24: "important",
  airline: "info",
  country: "info",
  registration: "important",
  type_code: "info",
  route: "important",
  airport: "info",
  area: "info",
  altitude_min: "important",
  speed_min: "important",
  takeoff: "critical",
  landing: "critical",
};

function normalizeText(value) {
  return String(value ?? "").trim();
}

function normalizeSearchBlob(value) {
  return normalizeText(value).toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function normalizeNumber(value) {
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : null;
}

export function getAlertRuleLabel(type) {
  return ALERT_RULE_LABELS[type] ?? "Rule";
}

export function getAlertSeverityLabel(value) {
  return ALERT_SEVERITY_OPTIONS.find((option) => option.value === value)?.label ?? "Info";
}

export function getAlertRuleOption(type) {
  return ALERT_RULE_OPTIONS.find((option) => option.value === type) ?? null;
}

export function getAlertRuleDefaultSeverity(type) {
  return DEFAULT_ALERT_SEVERITY[type] ?? "info";
}

export function normalizeAlertRuleDraft(rule) {
  const type = normalizeText(rule?.type);
  if (!type) {
    return null;
  }

  const option = getAlertRuleOption(type);
  const query = normalizeText(rule?.query);
  const severity = ALERT_SEVERITY_OPTIONS.some((entry) => entry.value === rule?.severity)
    ? rule.severity
    : getAlertRuleDefaultSeverity(type);
  const cooldownMinutes = Math.max(1, Math.min(180, Math.round(normalizeNumber(rule?.cooldownMinutes) ?? DEFAULT_ALERT_COOLDOWN_MINUTES)));

  if (type === "altitude_min" || type === "speed_min") {
    const threshold = normalizeNumber(query);
    if (threshold === null || threshold < 0) {
      return null;
    }

    return {
      type,
      query: String(Math.round(threshold)),
      payload: {
        threshold: Math.round(threshold),
      },
      severity,
      cooldownMinutes,
    };
  }

  if (type === "takeoff" || type === "landing") {
    return {
      type,
      query: query || option?.placeholder || DEFAULT_TRANSITION_QUERY,
      payload: rule?.payload ?? null,
      severity,
      cooldownMinutes,
    };
  }

  if (!query) {
    return null;
  }

  return {
    type,
    query,
    payload: rule?.payload ?? null,
    severity,
    cooldownMinutes,
  };
}

export function buildAlertEventFingerprint(rule, eventType, flight = null) {
  const ruleId = normalizeText(rule?.id || `${rule?.type}:${rule?.query}`).toLowerCase();
  const flightKey = normalizeText(flight?.icao24 ?? flight?.registration ?? "").toLowerCase();
  return [ruleId, normalizeText(eventType).toLowerCase(), flightKey].filter(Boolean).join(":");
}

export function matchesAlertRule(flight, rule, helpers = {}) {
  const normalizedQuery = normalizeText(rule?.query).toLowerCase();
  const threshold = normalizeNumber(rule?.payload?.threshold ?? rule?.query);

  if (rule?.type === "callsign") {
    return (flight?.callsign ?? "").toLowerCase().includes(normalizedQuery);
  }

  if (rule?.type === "airline") {
    return deriveOperatorCode(flight).toLowerCase().includes(normalizedQuery);
  }

  if (rule?.type === "country") {
    return (flight?.origin_country ?? "").toLowerCase().includes(normalizedQuery);
  }

  if (rule?.type === "registration") {
    return (flight?.registration ?? "").toLowerCase().includes(normalizedQuery);
  }

  if (rule?.type === "type_code") {
    return (flight?.type_code ?? "").toLowerCase().includes(normalizedQuery);
  }

  if (rule?.type === "route") {
    const normalizedRouteQuery = normalizeSearchBlob(rule?.query);
    return [
      flight?.route_label,
      flight?.route_verbose,
      flight?.airport_codes,
      flight?.iata_codes,
      flight?.origin,
      flight?.destination,
      flight?.origin_iata,
      flight?.origin_icao,
      flight?.destination_iata,
      flight?.destination_icao,
    ]
      .filter(Boolean)
      .some((value) => {
        const rawValue = String(value).toLowerCase();
        return (
          rawValue.includes(normalizedQuery) ||
          normalizeSearchBlob(value).includes(normalizedRouteQuery)
        );
      });
  }

  if (rule?.type === "airport") {
    const radiusKm = normalizeNumber(rule?.payload?.radiusKm ?? 48);
    if (
      !Number.isFinite(rule?.payload?.latitude) ||
      !Number.isFinite(rule?.payload?.longitude) ||
      radiusKm === null ||
      typeof helpers.calculateDistanceKm !== "function"
    ) {
      return false;
    }

    return (
      helpers.calculateDistanceKm(flight?.latitude, flight?.longitude, {
        center: [rule.payload.latitude, rule.payload.longitude],
      }) <= radiusKm
    );
  }

  if (rule?.type === "area") {
    if (typeof helpers.isFlightInsideBbox !== "function") {
      return false;
    }

    return helpers.isFlightInsideBbox(flight, rule?.payload?.bbox ?? null);
  }

  if (rule?.type === "altitude_min") {
    return threshold !== null && Number(flight?.altitude) >= threshold;
  }

  if (rule?.type === "speed_min") {
    return threshold !== null && Number(flight?.velocity ?? 0) * 3.6 >= threshold;
  }

  if (rule?.type === "takeoff" || rule?.type === "landing") {
    return false;
  }

  return (flight?.icao24 ?? "").toLowerCase().includes(normalizedQuery);
}

export function findTransitionAlertMatches(flights, previousFlightsByIcao24, rule) {
  if (rule?.type !== "takeoff" && rule?.type !== "landing") {
    return [];
  }

  const transitionToGround = rule.type === "landing";
  const matches = [];

  for (const flight of flights ?? []) {
    const previousFlight = previousFlightsByIcao24?.get?.(flight?.icao24) ?? null;
    if (!previousFlight) {
      continue;
    }

    const previousOnGround = Boolean(previousFlight.on_ground);
    const currentOnGround = Boolean(flight?.on_ground);

    if (transitionToGround && !previousOnGround && currentOnGround) {
      matches.push(flight);
      continue;
    }

    if (!transitionToGround && previousOnGround && !currentOnGround) {
      matches.push(flight);
    }
  }

  return matches;
}
