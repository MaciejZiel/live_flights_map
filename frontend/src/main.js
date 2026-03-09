import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "./app.css";

import { mount } from "svelte";

import App from "./App.svelte";

mount(App, {
  target: document.getElementById("app"),
});
