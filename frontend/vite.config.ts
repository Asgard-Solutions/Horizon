import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const hmrPort = env.WDS_SOCKET_PORT ? Number(env.WDS_SOCKET_PORT) : undefined;
  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 3000,
      allowedHosts: true,
      hmr: hmrPort ? { clientPort: hmrPort } : undefined,
      // Local development: forward API calls to the Python server started with `python run.py`.
      proxy: { "/api": { target: env.MC_DEV_API || "http://127.0.0.1:8765", changeOrigin: false } },
    },
    build: { outDir: "dist", sourcemap: false },
  };
});
