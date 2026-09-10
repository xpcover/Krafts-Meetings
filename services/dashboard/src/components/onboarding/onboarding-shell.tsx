"use client";

import { cn } from "@/lib/utils";

interface OnboardingShellProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Phone-first frame shared by every onboarding screen. Fills the viewport on a
 * handset and centres a 390px column on wider screens so the same layout can be
 * installed as a PWA or opened on desktop.
 */
export function OnboardingShell({ children, className }: OnboardingShellProps) {
  return (
    <div className="min-h-[100dvh] bg-background flex justify-center">
      <div
        className={cn(
          "flex w-full max-w-[390px] flex-col px-6 pb-7 pt-6",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}
