import pluginJs from '@eslint/js';

export default [
  { files: ['**/*.js'], languageOptions: { sourceType: 'script' } },
  pluginJs.configs.recommended,
];
