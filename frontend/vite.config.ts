import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The backend (FastAPI) enables permissive CORS, so the dev server talks to it
// directly via VITE_API_BASE (default http://localhost:8000) — no proxy needed.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
});
