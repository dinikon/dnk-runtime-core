import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";

export default [
    {
        ignores: ["dist/**", "node_modules/**"],
    },
    ...tseslint.configs.recommended,
    ...pluginVue.configs["flat/essential"],
    {
        rules: {
            "no-debugger": "error",
            "no-dupe-keys": "error",
            "no-empty": "error",
            "no-irregular-whitespace": "error",
            "no-unreachable": "error",
            "no-unsafe-finally": "error",
            "no-useless-catch": "error",
        },
    },
    {
        files: ["src/**/*.{ts,vue}"],
        languageOptions: {
            parserOptions: {
                parser: tseslint.parser,
                ecmaVersion: "latest",
                sourceType: "module",
            },
        },
    },
    {
        files: ["src/**/*.vue"],
        rules: {
            "vue/multi-word-component-names": "off",
        },
    },
];
