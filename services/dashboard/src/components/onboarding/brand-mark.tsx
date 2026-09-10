import { cn } from "@/lib/utils";

/**
 * Contact-card mark used on the onboarding screens. Drawn inline so it inherits
 * currentColor and stays crisp at any density.
 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={cn("h-11 w-11 text-foreground", className)}
    >
      <rect x="2" y="5" width="20" height="14" rx="2.5" />
      <circle cx="8.5" cy="11" r="2.25" />
      <path d="M5 16.25c.6-1.5 2-2.25 3.5-2.25s2.9.75 3.5 2.25" />
      <path d="M15.5 10h4" />
      <path d="M15.5 13.5h2.5" />
    </svg>
  );
}
