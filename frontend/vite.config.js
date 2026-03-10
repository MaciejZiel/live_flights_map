import { defineConfig, loadEnv } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const host = env.VITE_DEV_HOST || "127.0.0.1";
  const port = Number(env.VITE_DEV_PORT || "5173");
  const apiBaseUrl = env.VITE_API_BASE_URL?.trim() || "";
  const proxyTarget =
    env.VITE_DEV_PROXY_TARGET?.trim() || apiBaseUrl || "http://127.0.0.1:5000";
  const useDevProxy = !apiBaseUrl;

  return {
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
