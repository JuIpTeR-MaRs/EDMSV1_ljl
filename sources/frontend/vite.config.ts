import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import fs from "fs";

// Resolve paths to mkcert certificates in the repository root directory
const sslKeyPath = path.resolve(__dirname, "../../localhost+2-key.pem");
const sslCertPath = path.resolve(__dirname, "../../localhost+2.pem");

const hasCert = fs.existsSync(sslKeyPath) && fs.existsSync(sslCertPath);

export default defineConfig({
  envDir: path.resolve(__dirname, "../../"),
  plugins: [vue()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    https: hasCert ? {
      key: fs.readFileSync(sslKeyPath),
      cert: fs.readFileSync(sslCertPath),
    } : undefined,
    proxy: {
      "/api": { target: "http://127.0.0.1:5000", changeOrigin: true },
      "/socket.io": {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        ws: true
      },
      "/static": { target: "http://127.0.0.1:5000", changeOrigin: true },
    },
  },
});