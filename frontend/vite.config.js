import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    chunkSizeWarningLimit: 700,   // recharts is large by nature; it sits in its own cached chunk
    rollupOptions: {
      output: {
        // keep the app bundle small: heavy libraries get their own cached chunks
        manualChunks: {
          react: ["react", "react-dom"],
          charts: ["recharts"],
          geo: ["d3-geo"],
        },
      },
    },
  },
});
