import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The configurator SPA. Dev server runs on 5173 (the origin the FastAPI
// backend allow-lists for CORS).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
});
