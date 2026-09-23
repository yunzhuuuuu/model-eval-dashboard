import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Retrieval Lab | Model Evaluation Dashboard",
  description:
    "Explore retrieval datasets, upload your own, and compare embedding models.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
