/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "Noto Sans",
          "PingFang SC",
          "Microsoft YaHei",
          "sans-serif",
        ],
        story: ['"Merriweather"', '"Noto Serif SC"', "Georgia", "Times New Roman", "serif"],
      },
      colors: {
        glass: "rgba(15, 23, 42, 0.55)",
        glassBorder: "rgba(148, 163, 184, 0.18)",
      },
      boxShadow: {
        glow: "0 0 24px rgba(56, 189, 248, 0.15)",
      },
    },
  },
  plugins: [],
};
