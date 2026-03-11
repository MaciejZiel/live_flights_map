function getPalette(flight, dimmed, watchModeEnabled) {
  if (dimmed) {
    return {
      fill: [0.537, 0.576, 0.627, 0.28],
      stroke: [0.239, 0.274, 0.314, 0.38],
      size: 4.4,
    };
  }

  if (watchModeEnabled) {
    return {
      fill: [0.604, 0.647, 0.702, 0.52],
      stroke: [0.294, 0.333, 0.388, 0.62],
      size: flight.on_ground ? 4.6 : 5,
    };
  }

  if (flight.on_ground) {
    return {
      fill: [0.769, 0.518, 0.086, 0.52],
      stroke: [0.29, 0.216, 0.024, 0.68],
      size: 4.3,
    };
  }

  return {
    fill: [0.969, 0.78, 0.086, 0.72],
    stroke: [0.275, 0.216, 0.039, 0.78],
    size: 5.2,
  };
}

function buildShader(gl, type, source) {
  const shader = gl.createShader(type);
  if (!shader) {
    throw new Error("Unable to allocate WebGL shader.");
  }
  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader) || "Unknown shader compilation failure.";
    gl.deleteShader(shader);
    throw new Error(info);
  }

  return shader;
}

function buildProgram(gl) {
  const vertexSource = `
    attribute vec2 a_position;
    attribute float a_size;
    attribute vec4 a_fill;
    attribute vec4 a_stroke;

    uniform vec2 u_resolution;

    varying vec4 v_fill;
    varying vec4 v_stroke;

    void main() {
      vec2 zeroToOne = a_position / u_resolution;
      vec2 zeroToTwo = zeroToOne * 2.0;
      vec2 clipSpace = zeroToTwo - 1.0;
      gl_Position = vec4(clipSpace * vec2(1.0, -1.0), 0.0, 1.0);
      gl_PointSize = a_size;
      v_fill = a_fill;
      v_stroke = a_stroke;
    }
  `;

  const fragmentSource = `
    precision mediump float;

    varying vec4 v_fill;
    varying vec4 v_stroke;

    void main() {
      vec2 centered = gl_PointCoord - vec2(0.5, 0.5);
      float distanceFromCenter = length(centered);
      if (distanceFromCenter > 0.5) {
        discard;
      }

      float outerEdge = smoothstep(0.46, 0.5, distanceFromCenter);
      vec4 color = mix(v_fill, v_stroke, outerEdge);
      gl_FragColor = color;
    }
  `;

  const vertexShader = buildShader(gl, gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = buildShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();

  if (!program) {
    throw new Error("Unable to allocate WebGL program.");
  }

  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program) || "Unknown program link failure.";
    gl.deleteProgram(program);
    throw new Error(info);
  }

  return {
    program,
    positionLocation: gl.getAttribLocation(program, "a_position"),
    sizeLocation: gl.getAttribLocation(program, "a_size"),
    fillLocation: gl.getAttribLocation(program, "a_fill"),
    strokeLocation: gl.getAttribLocation(program, "a_stroke"),
    resolutionLocation: gl.getUniformLocation(program, "u_resolution"),
  };
}

export function createAircraftWebGlOverlay(canvas) {
  if (!canvas) {
    return null;
  }

  const gl =
    canvas.getContext("webgl", {
      alpha: true,
      antialias: true,
      premultipliedAlpha: false,
      preserveDrawingBuffer: false,
    }) ??
    canvas.getContext("experimental-webgl");

  if (!gl) {
    return null;
  }

  const { program, positionLocation, sizeLocation, fillLocation, strokeLocation, resolutionLocation } =
    buildProgram(gl);
  const positionBuffer = gl.createBuffer();
  const sizeBuffer = gl.createBuffer();
  const fillBuffer = gl.createBuffer();
  const strokeBuffer = gl.createBuffer();

  if (!positionBuffer || !sizeBuffer || !fillBuffer || !strokeBuffer) {
    throw new Error("Unable to allocate WebGL buffers.");
  }

  gl.useProgram(program);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  return {
    gl,
    program,
    positionLocation,
    sizeLocation,
    fillLocation,
    strokeLocation,
    resolutionLocation,
    positionBuffer,
    sizeBuffer,
    fillBuffer,
    strokeBuffer,
  };
}

function setAttribute(gl, buffer, location, size, data) {
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
  gl.enableVertexAttribArray(location);
  gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
}

export function resizeAircraftWebGlOverlay(overlay, canvas, width, height) {
  if (!overlay || !canvas) {
    return false;
  }

  const pixelRatio = window.devicePixelRatio || 1;
  const nextWidth = Math.max(1, Math.round(width * pixelRatio));
  const nextHeight = Math.max(1, Math.round(height * pixelRatio));

  if (canvas.width !== nextWidth || canvas.height !== nextHeight) {
    canvas.width = nextWidth;
    canvas.height = nextHeight;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
  }

  overlay.gl.viewport(0, 0, nextWidth, nextHeight);
  return true;
}

export function clearAircraftWebGlOverlay(overlay) {
  if (!overlay) {
    return;
  }

  const { gl } = overlay;
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
}

export function drawAircraftWebGlOverlay(
  overlay,
  canvas,
  {
    map,
    flights = [],
    selectedIcao24 = null,
    watchedIcao24s = [],
    dimmedIcao24s = [],
    watchModeEnabled = false,
    active = false,
    marginPx = 12,
  } = {}
) {
  if (!overlay || !canvas || !map) {
    return;
  }

  const { gl, program, positionLocation, sizeLocation, fillLocation, strokeLocation, resolutionLocation } = overlay;
  const bounds = map.getSize();
  const width = bounds.x;
  const height = bounds.y;
  resizeAircraftWebGlOverlay(overlay, canvas, width, height);

  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  if (!active) {
    return;
  }

  const selectedIds = new Set([selectedIcao24, ...watchedIcao24s].filter(Boolean));
  const dimmedIds = new Set(dimmedIcao24s);

  const positions = [];
  const fills = [];
  const strokes = [];
  const sizes = [];

  for (const flight of flights) {
    if (
      !flight?.icao24 ||
      selectedIds.has(flight.icao24) ||
      !Number.isFinite(flight.latitude) ||
      !Number.isFinite(flight.longitude)
    ) {
      continue;
    }

    const point = map.latLngToContainerPoint([flight.latitude, flight.longitude]);
    if (
      point.x < -marginPx ||
      point.y < -marginPx ||
      point.x > width + marginPx ||
      point.y > height + marginPx
    ) {
      continue;
    }

    const palette = getPalette(flight, dimmedIds.has(flight.icao24), watchModeEnabled);
    positions.push(point.x, point.y);
    sizes.push(palette.size);
    fills.push(...palette.fill);
    strokes.push(...palette.stroke);
  }

  if (!positions.length) {
    return;
  }

  gl.useProgram(program);
  gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
  setAttribute(gl, overlay.positionBuffer, positionLocation, 2, new Float32Array(positions));
  setAttribute(gl, overlay.sizeBuffer, sizeLocation, 1, new Float32Array(sizes));
  setAttribute(gl, overlay.fillBuffer, fillLocation, 4, new Float32Array(fills));
  setAttribute(gl, overlay.strokeBuffer, strokeLocation, 4, new Float32Array(strokes));
  gl.drawArrays(gl.POINTS, 0, sizes.length);
}

export function destroyAircraftWebGlOverlay(overlay) {
  if (!overlay) {
    return;
  }

  const { gl, program, positionBuffer, sizeBuffer, fillBuffer, strokeBuffer } = overlay;
  if (positionBuffer) {
    gl.deleteBuffer(positionBuffer);
  }
  if (sizeBuffer) {
    gl.deleteBuffer(sizeBuffer);
  }
  if (fillBuffer) {
    gl.deleteBuffer(fillBuffer);
  }
  if (strokeBuffer) {
    gl.deleteBuffer(strokeBuffer);
  }
  if (program) {
    gl.deleteProgram(program);
  }
}
