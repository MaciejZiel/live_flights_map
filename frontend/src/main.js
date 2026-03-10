import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "./app.css";

import { mount } from "svelte";

import App from "./App.svelte";

const appTarget = document.getElementById("app");
const bootFallback = document.getElementById("boot-fallback");
const bootBadge = document.querySelector("[data-boot-badge]");
const bootMessage = document.querySelector("[data-boot-message]");

function updateBootState(state, message, error = null) {
  if (bootFallback) {
    bootFallback.hidden = false;
    bootFallback.dataset.state = state;
  }

  if (bootBadge) {
    bootBadge.textContent = state === "error" ? "Startup error" : "Loading";
  }

  if (bootMessage) {
    bootMessage.textContent = message;
  }

  if (error) {
    window.__APP_STARTUP_ERROR__ = {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : null,
    };
  }
}

window.addEventListener("error", (event) => {
  console.error("[frontend startup error]", event.error ?? event.message ?? event);

  if (!appTarget?.childElementCount) {
    updateBootState(
      "error",
      "The frontend crashed before it finished rendering. Open DevTools and inspect Console and Network for failed bundles or startup errors.",
      event.error ?? event.message ?? event
    );
  }
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("[frontend startup rejection]", event.reason ?? event);

  if (!appTarget?.childElementCount) {
    updateBootState(
      "error",
      "The frontend hit an unhandled startup error. Open DevTools and inspect Console and Network for failed bundles or startup errors.",
      event.reason ?? event
    );
  }
});

try {
  if (!appTarget) {
    throw new Error("Missing #app mount target.");
  }

  mount(App, {
    target: appTarget,
  });

  requestAnimationFrame(() => {
    if (appTarget.childElementCount > 0 && bootFallback) {
      bootFallback.remove();
    } else {
      updateBootState(
        "error",
        "The frontend bundle loaded but the app did not finish mounting. Open DevTools and inspect Console for startup errors."
      );
    }
  });
} catch (error) {
  console.error("[frontend mount failed]", error);
  updateBootState(
    "error",
    "The frontend failed during initial mount. Open DevTools and inspect Console for the exact startup error.",
    error
  );
}
