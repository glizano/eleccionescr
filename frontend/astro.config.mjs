// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  vite: {
    define: {
      'import.meta.env.PUBLIC_BACKEND_URL': JSON.stringify(
        process.env.PUBLIC_BACKEND_URL || 'http://localhost:8000'
      ),
    },
  },
});
