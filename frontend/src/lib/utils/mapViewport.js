export function normalizeMapViewport(candidate) {
  const latitude = Number(candidate?.center?.[0]);
  const longitude = Number(candidate?.center?.[1]);
  const zoom = Number(candidate?.zoom);

  if (
    !Number.isFinite(latitude) ||
    latitude < -85 ||
    latitude > 85 ||
    !Number.isFinite(longitude) ||
    longitude < -180 ||
    longitude > 180 ||
    !Number.isFinite(zoom) ||
    zoom < 2 ||
    zoom > 18
  ) {
    return null;
  }

  return { center: [latitude, longitude], zoom };
}
