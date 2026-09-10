"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { BackButton } from "@/components/onboarding/back-button";
import { FormError } from "@/components/onboarding/form-error";
import { OnboardingField } from "@/components/onboarding/onboarding-field";
import { OnboardingShell } from "@/components/onboarding/onboarding-shell";
import {
  GoogleButton,
  MicrosoftButton,
  SsoDivider,
  useAuthMethods,
} from "@/components/onboarding/auth-methods";
import { useAuthStore } from "@/stores/auth-store";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function SignInPage() {
  const router = useRouter();
  const sendMagicLink = useAuthStore((s) => s.sendMagicLink);
  const { googleEnabled, microsoftEnabled } = useAuthMethods();

  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const trimmed = email.trim();
    if (!EMAIL_PATTERN.test(trimmed)) {
      setError("Enter a valid work email address.");
      return;
    }

    setSubmitting(true);
    setError("");

    const result = await sendMagicLink(trimmed);

    if (!result.success) {
      setSubmitting(false);
      setError(result.error || "We couldn't send your sign-in link. Try again.");
      return;
    }

    // Without SMTP the backend signs the user straight in.
    if (result.mode === "direct") {
      router.push("/");
      return;
    }

    router.push(`/start/check-email?email=${encodeURIComponent(trimmed)}`);
  };

  const hasSso = googleEnabled || microsoftEnabled;

  return (
    <OnboardingShell>
      <BackButton href="/start" />

      <div className="mt-5 flex flex-col gap-2">
        <h1 className="text-[28px] font-semibold leading-tight tracking-tight">
          Welcome back
        </h1>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          Sign in to reach your contacts and drafts.
        </p>
      </div>

      <form noValidate onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
        <OnboardingField
          id="email"
          label="Work email"
          type="email"
          inputMode="email"
          autoComplete="email"
          autoFocus
          placeholder="you@company.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setError("");
          }}
        />

        {error ? <FormError message={error} /> : null}

        <button
          type="submit"
          disabled={email.trim().length === 0 || submitting}
          className="mt-1 flex h-[52px] w-full items-center justify-center gap-2 rounded-lg bg-primary text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-35"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {submitting ? "Sending link…" : "Email me a sign-in link"}
        </button>
      </form>

      {hasSso ? (
        <>
          <SsoDivider />
          <div className="flex flex-col gap-2.5">
            {googleEnabled ? <GoogleButton /> : null}
            {microsoftEnabled ? <MicrosoftButton /> : null}
          </div>
        </>
      ) : null}

      <div className="flex-1" />

      <p className="text-center text-sm text-muted-foreground">
        New here?{" "}
        <Link href="/start/signup" className="font-medium text-foreground hover:underline">
          Create an account
        </Link>
      </p>
    </OnboardingShell>
  );
}
