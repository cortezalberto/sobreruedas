/// <reference types="vitest" />
import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';

/**
 * Vitest — T-003, job `test-frontend`.
 *
 * Este archivo NO lo declara ninguna tarea `T-XXX`: T-003 exige el job
 * `vitest run con coverage` pero nadie crea la configuracion. Mismo patron
 * huerfano que `backend/pyproject.toml`. Se atribuye a T-003, que es quien lo
 * necesita.
 */
// Sin `@vitejs/plugin-react`: vitest transforma JSX con esbuild leyendo
// `jsx: react-jsx` del tsconfig, y alcanza para tests de componentes.
//
// Se quito ademas porque su version 6 exige vite ^8, y esa cadena arrastraba
// vulnerabilidades altas y criticas que bloquearian el job de seguridad.
// Sin el plugin: 0 vulnerabilidades y los tests corren igual.
export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/unit/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        // Sin logica: solo declara metadatos y monta el arbol.
        'src/app/layout.tsx',
      ],
    },
  },
  resolve: {
    // Los mismos alias que tsconfig.json. Vitest no lee `paths` de TypeScript.
    alias: { '@': resolve(__dirname, './src') },
  },
});
