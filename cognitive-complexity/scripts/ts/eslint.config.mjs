// Self-contained flat config for cognitive-complexity scoring of JS/TS files.
// Threshold 0 makes eslint-plugin-sonarjs report EVERY function with its score,
// which run.mjs / cogcom.py parse out. Not meant for general linting.
import sonarjs from 'eslint-plugin-sonarjs';
import tsParser from '@typescript-eslint/parser';

export default [
  {
    files: ['**/*.{js,jsx,ts,tsx,mjs,cjs}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
    },
    plugins: { sonarjs },
    rules: { 'sonarjs/cognitive-complexity': ['warn', 0] },
  },
];
