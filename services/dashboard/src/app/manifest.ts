import type { MetadataRoute } from "next";
import { withBasePath } from "@/lib/base-path";

/**
 * Installable PWA manifest. Launching goes to the onboarding entry point; the
 * auth provider forwards an already-signed-in user on to the dashboard.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Krafts Meetings",
    short_name: "Krafts",
    description:
      "Capture business cards, keep every conversation in context, and send the follow-up.",
    start_url: withBasePath("/start"),
    scope: withBasePath("/"),
    display: "standalone",
    orientation: "portrait",
    background_color: "#ffffff",
    theme_color: "#ffffff",
    icons: [
      {
        src: withBasePath("/icons/vexadark.svg"),
        type: "image/svg+xml",
        sizes: "any",
        purpose: "any",
      },
    ],
  };
}
