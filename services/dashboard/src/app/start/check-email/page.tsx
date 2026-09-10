"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Loader2, Mail } from "lucide-react";
import { BackButton } from "@/components/onboarding/back-button";
import { FormError } from "@/components/onboarding/form-error";
import { OnboardingShell } from "@/components/onboarding/onboarding-shell";
import { useAuthStore } from "@/stores/auth-store";

const RESEND_COOLDOWN_SECONDS = 30;

function CheckEmailContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";
  const sendMagicLink = useAuthStore((s) => s.sendMagicLink);

  const [secondsLeft, setSecondsLeft] = useState(0);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  const startCooldown = () => {
    setSecondsLeft(RESEND_COOLDOWN_SECONDS);
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => {
      setSecondsLeft((current) => {
        if (current <= 1 && timer.current) {
          clearInterval(timer.current);
          timer.current = null;
        }
        return current > 0 ? current - 1 : 0;
      });
    }, 1000);
  };

  const handleResend = async () => {
    if (!email || secondsLeft > 0 || sending) return;

    setSending(true);
    setError("");

    const result = await sendMagicLink(email);
    setSending(false);

    if (!result.success) {
      setError(result.error || "We couldn't resend the link. Try again shortly.");
      return;
    }

    startCooldown();
  };

  const resendLabel = sending
    ? "Sending…"
    : secondsLeft > 0
      ? `Resend in ${secondsLeft}s`
      : "Resend link";

  return (
    <OnboardingShell>
      <BackButton href="/start/signin" />

      <div className="flex flex-1 flex-col items-center justify-center gap-6 pb-10 text-center">
        <div className="flex h-[68px] w-[68px] items-center justify-center rounded-full bg-accent">
          <Mail className="h-[30px] w-[30px] text-foreground" strokeWidth={1.5} />
        </div>

        <div className="flex flex-col gap-2.5">
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight">
            Check your email
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground text-pretty">
            We sent a sign-in link to
            <br />
            <span className="font-medium text-foreground">
              {email || "your inbox"}
            </span>
            . It expires in 15 minutes.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {error ? <FormError message={error} /> : null}

        <button
          type="button"
          onClick={handleResend}
          disabled={!email || secondsLeft > 0 || sending}
          className="flex h-[52px] w-full items-center justify-center gap-2 rounded-lg bg-primary text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-35"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {resendLabel}
        </button>

        <Link
          href="/start/signin"
          className="flex h-[52px] w-full items-center justify-center rounded-lg border border-border bg-background text-base font-medium text-foreground transition-colors hover:bg-accent"
        >
          Use a different email
        </Link>

        <p className="mt-1.5 text-center text-[13px] leading-relaxed text-muted-foreground">
          Nothing yet? Check spam, or{" "}
          <Link href="/start/signin" className="font-medium text-foreground hover:underline">
            try another address
          </Link>
          .
        </p>
      </div>
    </OnboardingShell>
  );
}

export default function CheckEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[100dvh] items-center justify-center bg-background">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <CheckEmailContent />
    </Suspense>
  );
}
