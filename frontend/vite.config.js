import { defineConfig, loadEnv } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

function normalizeBasePath(value) {
  const rawValue = String(value ?? "/").trim();
  if (!rawValue || rawValue === "/") {
    return "/";
  }

  const withLeadingSlash = rawValue.startsWith("/") ? rawValue : `/${rawValue}`;
  return withLeadingSlash.endsWith("/") ? withLeadingSlash : `${withLeadingSlash}/`;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const host = env.VITE_DEV_HOST || "127.0.0.1";
  const port = Number(env.VITE_DEV_PORT || "5173");
  const apiBaseUrl = env.VITE_API_BASE_URL?.trim() || "";
  const base = normalizeBasePath(env.VITE_BASE_PATH);
  const proxyTarget =
    env.VITE_DEV_PROXY_TARGET?.trim() || apiBaseUrl || "http://127.0.0.1:5000";
  const useDevProxy = !apiBaseUrl;

  return {
    base,
    plugins: [svelte()],
    server: {
      host,
      port,
      proxy: useDevProxy
        ? {
            "/api": {
              target: proxyTarget,
              changeOrigin: true,
            },
            "/health": {
              target: proxyTarget,
              changeOrigin: true,
            },
          }
        : undefined,
    },
  };
});
