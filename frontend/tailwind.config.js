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
        /** Chinese-first body (UI language 中文) */
        storyZh: ['"Noto Serif SC"', "Georgia", "Times New Roman", "serif"],
        /** English body: Source Serif 4 for comfortable long-form reading; CJK falls back to Noto */
        storyEn: ['"Source Serif 4"', '"Noto Serif SC"', "Georgia", "serif"],
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
