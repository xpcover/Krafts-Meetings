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

export default function SignUpPage() {
  const router = useRouter();
  const sendMagicLink = useAuthStore((s) => s.sendMagicLink);
  const { googleEnabled, microsoftEnabled } = useAuthMethods();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const ready =
    name.trim().length > 1 && EMAIL_PATTERN.test(email.trim()) && agreed;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;

    setSubmitting(true);
    setError("");

    const trimmedEmail = email.trim();
    const result = await sendMagicLink(trimmedEmail, name.trim());

    if (!result.success) {
      setSubmitting(false);
      setError(result.error || "We couldn't create your account. Try again.");
      return;
    }

    if (result.mode === "direct") {
      router.push("/");
      return;
    }

    router.push(`/start/check-email?email=${encodeURIComponent(trimmedEmail)}`);
  };

  const hasSso = googleEnabled || microsoftEnabled;

  return (
    <OnboardingShell>
      <BackButton href="/start" />

      <div className="mt-4 flex flex-col gap-2">
        <h1 className="text-[28px] font-semibold leading-tight tracking-tight">
          Create your account
        </h1>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          We&apos;ll email you a link to finish — no password to remember.
        </p>
      </div>

      <form noValidate onSubmit={handleSubmit} className="mt-7 flex flex-col gap-3.5">
        <OnboardingField
          id="name"
          label="Full name"
          type="text"
          autoComplete="name"
          autoFocus
          placeholder="Priya Raman"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setError("");
          }}
        />

        <OnboardingField
          id="signup-email"
          label="Work email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setError("");
          }}
        />

        <label className="mt-1.5 flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-px size-5 shrink-0 cursor-pointer accent-primary"
          />
          <span className="text-[13px] leading-relaxed text-muted-foreground">
            I agree to the{" "}
            <Link href="/docs/terms" className="font-medium text-foreground hover:underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/docs/privacy" className="font-medium text-foreground hover:underline">
              Privacy Policy
            </Link>
            .
          </span>
        </label>

        {error ? <FormError message={error} /> : null}

        <button
          type="submit"
          disabled={!ready || submitting}
          className="mt-2 flex h-[52px] w-full items-center justify-center gap-2 rounded-lg bg-primary text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-35"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {submitting ? "Creating account…" : "Create account"}
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

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/start/signin" className="font-medium text-foreground hover:underline">
          Sign in
        </Link>
      </p>
    </OnboardingShell>
  );
}
