const LOCAL_REGION_CELL_DEGREES = 3;
const LOCAL_REGION_MIN_ZOOM = 6;

export function buildLocalRegionTile(viewBbox, zoom) {
  if (!viewBbox || !Number.isFinite(zoom) || zoom < LOCAL_REGION_MIN_ZOOM) {
    return null;
  }

  const centerLatitude = (viewBbox.lamin + viewBbox.lamax) / 2;
  const centerLongitude = (viewBbox.lomin + viewBbox.lomax) / 2;
  const latitudeIndex = Math.floor((centerLatitude + 90) / LOCAL_REGION_CELL_DEGREES);
  const longitudeIndex = Math.floor((centerLongitude + 180) / LOCAL_REGION_CELL_DEGREES);
  const lamin = Math.max(-90, -90 + latitudeIndex * LOCAL_REGION_CELL_DEGREES);
  const lomin = Math.max(-180, -180 + longitudeIndex * LOCAL_REGION_CELL_DEGREES);
  const bbox = {
    lamin,
    lamax: Math.min(90, lamin + LOCAL_REGION_CELL_DEGREES),
    lomin,
    lomax: Math.min(180, lomin + LOCAL_REGION_CELL_DEGREES),
  };

  return {
    key: `${latitudeIndex}:${longitudeIndex}`,
    bbox,
  };
}
