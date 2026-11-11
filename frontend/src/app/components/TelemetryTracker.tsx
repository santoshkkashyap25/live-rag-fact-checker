"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

export default function TelemetryTracker() {
  const pathname = usePathname();
  const lastLoggedPath = useRef<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Avoid duplicate logs for the exact same path in the same session cycle
    if (lastLoggedPath.current === pathname) return;
    lastLoggedPath.current = pathname;

    const payload = {
      path: pathname || window.location.pathname || "/",
      referrer: document.referrer || null,
    };

    fetch("/api/telemetry/visit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }).catch(() => {
      // Non-blocking telemetry failure is intentionally silent
    });
  }, [pathname]);

  return null;
}

