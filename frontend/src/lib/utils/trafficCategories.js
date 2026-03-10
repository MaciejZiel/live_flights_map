const CARGO_OPERATORS = new Set([
  "FDX",
  "UPS",
  "CLX",
  "BCS",
  "DHK",
  "EAT",
  "AHK",
  "BOX",
  "GTI",
  "ABW",
  "QTR",
]);

const MILITARY_OPERATORS = new Set([
  "RCH",
  "BAF",
  "AME",
  "ASY",
  "CNV",
  "HER",
  "NAF",
  "DUKE",
  "FORTE",
]);

const GOVERNMENT_OPERATORS = new Set([
  "SAM",
  "VPC",
  "NAX",
  "CFC",
  "GAF",
  "FNY",
]);

const BUSINESS_TYPE_PREFIXES = ["C", "G", "LJ", "FA", "E5", "PRM", "BE", "HDJ"];
const LIGHT_TYPE_PREFIXES = ["P28", "C15", "C17", "C18", "DA4", "PA2", "SR2", "M20", "RV"];
const HELICOPTER_PREFIXES = ["H", "EC", "AS3", "BK", "R44", "R66", "B06", "A109", "S76"];
const GLIDER_PREFIXES = ["GL", "LAK", "ASK", "DG", "LS", "ASW"];

function operatorFromCallsign(callsign) {
  const normalized = (callsign ?? "").trim().toUpperCase();
  const match = normalized.match(/^[A-Z]{3}/);
  return match ? match[0] : "";
}

function hasPrefix(value, prefixes) {
  const normalized = (value ?? "").trim().toUpperCase();
  if (!normalized) {
    return false;
  }

  return prefixes.some((prefix) => normalized.startsWith(prefix));
}

export const TRAFFIC_CATEGORY_OPTIONS = [
  { value: "all", label: "All traffic" },
  { value: "passenger", label: "Passenger" },
  { value: "cargo", label: "Cargo" },
  { value: "business", label: "Business" },
  { value: "military", label: "Military" },
  { value: "government", label: "Government" },
  { value: "helicopter", label: "Helicopter" },
  { value: "glider", label: "Glider" },
  { value: "light", label: "Light aircraft" },
  { value: "other", label: "Other" },
];

export function classifyTrafficCategory(flight) {
  const operator = operatorFromCallsign(flight?.callsign);
  const typeCode = (flight?.type_code ?? "").trim().toUpperCase();
  const altitude = Number(flight?.altitude);
  const speedKmh = Number(flight?.velocity ?? 0) * 3.6;

  if (CARGO_OPERATORS.has(operator)) {
    return "cargo";
  }

  if (MILITARY_OPERATORS.has(operator) || hasPrefix(typeCode, ["C13", "A400", "E3", "F16", "F18", "C17"])) {
    return "military";
  }

  if (GOVERNMENT_OPERATORS.has(operator)) {
    return "government";
  }

  if (hasPrefix(typeCode, HELICOPTER_PREFIXES)) {
    return "helicopter";
  }

  if (hasPrefix(typeCode, GLIDER_PREFIXES)) {
    return "glider";
  }

  if (hasPrefix(typeCode, LIGHT_TYPE_PREFIXES) || (speedKmh > 0 && speedKmh < 260 && altitude < 4500)) {
    return "light";
  }

  if (hasPrefix(typeCode, BUSINESS_TYPE_PREFIXES)) {
    return "business";
  }

  if (hasPrefix(typeCode, ["A", "B", "E19", "E17", "CRJ", "AT7", "AT4", "DH8"])) {
    return "passenger";
  }

  return "other";
}
