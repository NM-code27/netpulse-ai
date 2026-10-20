import { Suspense } from "react";
import { TopBar } from "@/components/TopBar";
import SiteDetailClient from "./SiteDetailClient";

export default function SiteDetailPage() {
  return (
    <Suspense
      fallback={
        <>
          <TopBar title="Site" />
          <div className="p-6" style={{ color: "var(--text-muted)" }}>Loading...</div>
        </>
      }
    >
      <SiteDetailClient />
    </Suspense>
  );
}
