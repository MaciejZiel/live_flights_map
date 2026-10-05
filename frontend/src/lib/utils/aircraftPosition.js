const POSITION_EPSILON = 0.000001;

export function hasFlightPositionChanged(current, next) {
  if (!current || !next) {
    return true;
  }

  return (
    Math.abs(Number(current[0]) - Number(next[0])) > POSITION_EPSILON ||
    Math.abs(Number(current[1]) - Number(next[1])) > POSITION_EPSILON
  );
}
