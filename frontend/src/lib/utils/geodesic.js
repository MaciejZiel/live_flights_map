const EARTH_RADIUS_KM = 6371;

function toRadians(value) {
  return (value * Math.PI) / 180;
}

function toDegrees(value) {
  return (value * 180) / Math.PI;
}

function normalizeLongitude(longitude) {
  const normalized = ((((longitude + 180) % 360) + 360) % 360) - 180;
  if (normalized === -180 && longitude > 0) {
    return 180;
  }
  return roundCoordinate(normalized);
}

function roundCoordinate(value) {
  return Number(value.toFixed(6));
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function centralAngle(start, end) {
  const startLatitude = toRadians(start[0]);
  const startLongitude = toRadians(start[1]);
  const endLatitude = toRadians(end[0]);
  const endLongitude = toRadians(end[1]);
  const deltaLongitude = endLongitude - startLongitude;
  const cosineValue =
    Math.sin(startLatitude) * Math.sin(endLatitude) +
    Math.cos(startLatitude) * Math.cos(endLatitude) * Math.cos(deltaLongitude);

  return Math.acos(clamp(cosineValue, -1, 1));
}

function interpolateGreatCirclePoint(start, end, fraction, angle) {
  if (!Number.isFinite(angle) || angle === 0) {
    return [roundCoordinate(start[0]), normalizeLongitude(start[1])];
  }

  const startLatitude = toRadians(start[0]);
  const startLongitude = toRadians(start[1]);
  const endLatitude = toRadians(end[0]);
  const endLongitude = toRadians(end[1]);
  const denominator = Math.sin(angle);
  const startWeight = Math.sin((1 - fraction) * angle) / denominator;
  const endWeight = Math.sin(fraction * angle) / denominator;
  const x =
    startWeight * Math.cos(startLatitude) * Math.cos(startLongitude) +
    endWeight * Math.cos(endLatitude) * Math.cos(endLongitude);
  const y =
    startWeight * Math.cos(startLatitude) * Math.sin(startLongitude) +
    endWeight * Math.cos(endLatitude) * Math.sin(endLongitude);
  const z = startWeight * Math.sin(startLatitude) + endWeight * Math.sin(endLatitude);
  const latitude = Math.atan2(z, Math.sqrt(x * x + y * y));
  const longitude = Math.atan2(y, x);

  return [roundCoordinate(toDegrees(latitude)), normalizeLongitude(toDegrees(longitude))];
}

export function buildGreatCircleSegments(
  routeLatLngs,
  options = {}
) {
  const normalizedRoute = (routeLatLngs ?? []).filter(
    (point) =>
      Array.isArray(point) &&
      point.length >= 2 &&
      Number.isFinite(point[0]) &&
      Number.isFinite(point[1])
  );
  if (normalizedRoute.length < 2) {
    return [];
  }

  const segments = [];

  for (let index = 0; index < normalizedRoute.length - 1; index += 1) {
    const legSegments = buildGreatCircleLegSegments(
      normalizedRoute[index],
      normalizedRoute[index + 1],
      options
    );

    for (const legSegment of legSegments) {
      if (legSegment.length < 2) {
        continue;
      }

      const previousSegment = segments[segments.length - 1];
      if (
        previousSegment &&
        previousSegment[previousSegment.length - 1][0] === legSegment[0][0] &&
        previousSegment[previousSegment.length - 1][1] === legSegment[0][1]
      ) {
        previousSegment.push(...legSegment.slice(1));
        continue;
      }

      segments.push(legSegment);
    }
  }

  return segments;
}

export function buildGreatCircleLegSegments(start, end, options = {}) {
  const angle = centralAngle(start, end);
  if (!Number.isFinite(angle) || angle === 0) {
    return [[
      [roundCoordinate(start[0]), normalizeLongitude(start[1])],
      [roundCoordinate(end[0]), normalizeLongitude(end[1])],
    ]];
  }

  const maxPoints = Math.max(8, Math.floor(options.maxPoints ?? 64));
  const stepKm = Math.max(40, Number(options.stepKm ?? 180));
  const distanceKm = angle * EARTH_RADIUS_KM;
  const pointCount = clamp(Math.ceil(distanceKm / stepKm) + 1, 8, maxPoints);
  const segments = [];
  let currentSegment = [];

  for (let index = 0; index < pointCount; index += 1) {
    const fraction = pointCount === 1 ? 0 : index / (pointCount - 1);
    const point =
      index === 0
        ? [roundCoordinate(start[0]), normalizeLongitude(start[1])]
        : index === pointCount - 1
          ? [roundCoordinate(end[0]), normalizeLongitude(end[1])]
          : interpolateGreatCirclePoint(start, end, fraction, angle);
    const previousPoint = currentSegment[currentSegment.length - 1];

    if (previousPoint && Math.abs(point[1] - previousPoint[1]) > 180) {
      if (currentSegment.length >= 2) {
        segments.push(currentSegment);
      }
      currentSegment = [previousPoint, point];
      continue;
    }

    currentSegment.push(point);
  }

  if (currentSegment.length >= 2) {
    segments.push(currentSegment);
  }

  return segments;
}
