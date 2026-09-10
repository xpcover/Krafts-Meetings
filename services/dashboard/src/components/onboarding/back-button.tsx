"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";

/**
 * 44px touch target, flush with the screen's left gutter.
 */
export function BackButton({ href }: { href?: string }) {
  const router = useRouter();

  return (
    <button
      type="button"
      aria-label="Go back"
      onClick={() => (href ? router.push(href) : router.back())}
      className="-ml-2.5 flex h-11 w-11 items-center justify-center rounded-lg text-foreground transition-colors hover:bg-accent"
    >
      <ChevronLeft className="h-[22px] w-[22px]" strokeWidth={1.7} />
    </button>
  );
}
