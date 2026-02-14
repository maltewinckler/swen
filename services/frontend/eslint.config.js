import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // Ignore build artifacts and generated output
  globalIgnores(['dist', 'coverage']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // This rule is useful as guidance, but too strict as an error for common
      // "reset on prop change" patterns in this codebase.
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
  // Vite React Fast Refresh rule is great for app code, but too noisy for entrypoints,
  // non-component utility modules, and test helpers.
  {
    files: [
      'src/main.tsx',
      'src/components/dashboard/widgets/shared/**',
      'src/components/ui/toast.tsx',
      'src/components/ui/tooltip.tsx',
      'src/routes/**/*.tsx',
      'tests/**/*.{ts,tsx}',
      'src/**/*.test.{ts,tsx}',
    ],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
