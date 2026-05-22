import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18212f",
        muted: "#64748b",
        panel: "#ffffff",
        line: "#d9e2ec",
        accent: "#0f766e",
        warning: "#b45309",
        danger: "#b91c1c"
      },
      boxShadow: {
        soft: "0 8px 20px rgba(15, 23, 42, 0.06)"
      }
    }
  },
  plugins: []
};

export default config;

