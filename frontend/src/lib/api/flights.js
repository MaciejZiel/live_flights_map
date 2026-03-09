const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchFlights() {
  const response = await fetch(`${API_BASE_URL}/api/flights`);
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error ?? "Failed to load flight positions.");
  }

  return payload;
}
