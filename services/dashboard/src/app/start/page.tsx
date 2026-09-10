import Link from "next/link";
import { BrandMark } from "@/components/onboarding/brand-mark";
import { OnboardingShell } from "@/components/onboarding/onboarding-shell";

const PROMISES = [
  "Cards captured in one tap",
  "Follow-ups written for you",
  "Works offline, syncs later",
];

export default function WelcomePage() {
  return (
    <OnboardingShell className="pt-8">
      <div className="flex flex-1 flex-col justify-center gap-7">
        <BrandMark />

        <div className="flex flex-col gap-3">
          <h1 className="text-[34px] font-semibold leading-[1.14] tracking-tight text-pretty">
            Every card,
            <br />
            every conversation,
            <br />
            one place.
          </h1>
          <p className="text-base leading-relaxed text-muted-foreground text-pretty">
            Snap a business card. Krafts Meetings files the contact, remembers the
            context, and drafts the follow-up.
          </p>
        </div>

        <ul className="flex flex-col gap-2.5">
          {PROMISES.map((promise) => (
            <li key={promise} className="flex items-center gap-2.5">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.6}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="h-[18px] w-[18px] text-muted-foreground"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
              <span className="text-sm text-foreground/70">{promise}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-col gap-3">
        <Link
          href="/start/signup"
          className="flex h-[52px] w-full items-center justify-center rounded-lg bg-primary text-base font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Create account
        </Link>
        <Link
          href="/start/signin"
          className="flex h-[52px] w-full items-center justify-center rounded-lg border border-border bg-background text-base font-medium text-foreground transition-colors hover:bg-accent"
        >
          I already have an account
        </Link>
        <p className="mt-1.5 text-center text-xs leading-relaxed text-muted-foreground">
          By continuing you agree to our{" "}
          <Link href="/docs/terms" className="font-medium text-foreground hover:underline">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/docs/privacy" className="font-medium text-foreground hover:underline">
            Privacy Policy
          </Link>
          .
        </p>
      </div>
    </OnboardingShell>
  );
}
