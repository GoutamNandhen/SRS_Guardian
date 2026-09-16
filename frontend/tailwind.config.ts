import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#091426",
          fixed: "#d8e3fb",
          container: "#1e293b",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#4b41e1",
          container: "#645efb",
          fixed: "#e2dfff",
          foreground: "#ffffff",
        },
        surface: {
          DEFAULT: "#f8f9ff",
          container: "#e5eeff",
          "container-low": "#eff4ff",
          "container-lowest": "#ffffff",
          "container-high": "#dce9ff",
          "container-highest": "#d3e4fe",
          dim: "#cbdbf5",
          bright: "#f8f9ff",
          variant: "#d3e4fe",
        },
        "on-surface": {
          DEFAULT: "#0b1c30",
          variant: "#45474c",
        },
        outline: {
          DEFAULT: "#75777d",
          variant: "#c5c6cd",
        },
        error: {
          DEFAULT: "#ba1a1a",
          container: "#ffdad6",
          foreground: "#ffffff",
        },
        "on-error-container": "#93000a",
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        lg: "0.25rem",
        xl: "0.5rem",
        full: "0.75rem",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
