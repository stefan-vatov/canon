import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://agentcanon.dev",
  // dist/ is the shipped Canon artifact directory (AGENTS.md, CLAUDE.md) —
  // the site builds beside it, never over it
  outDir: "./dist-site",
  server: {
    port: process.env.PORT ? Number(process.env.PORT) : 4321,
  },
});
