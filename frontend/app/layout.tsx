import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = { title: "UpSkill-AI Progress", description: "M3 progress tracking" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
