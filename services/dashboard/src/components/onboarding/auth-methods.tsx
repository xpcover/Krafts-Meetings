"use client";

import { useEffect, useState } from "react";
import { signIn } from "next-auth/react";
import { withBasePath } from "@/lib/base-path";

interface AuthHealth {
  authMode?: "direct" | "magic-link" | "google" | "entra-id" | "oauth";
  checks?: {
    googleOAuth?: { configured: boolean };
    azureAdOAuth?: { configured: boolean };
  };
}

/**
 * Reports which sign-in methods the deployment actually has configured, so the
 * onboarding screens never show a provider that cannot complete.
 */
export function useAuthMethods() {
  const [health, setHealth] = useState<AuthHealth | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch(withBasePath("/api/health"))
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled) setHealth(data);
      })
      .catch(() => {
        if (!cancelled) setHealth({});
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    loaded: health !== null,
    googleEnabled: health?.checks?.googleOAuth?.configured === true,
    microsoftEnabled: health?.checks?.azureAdOAuth?.configured === true,
    // Without SMTP the backend signs the user in directly instead of emailing.
    directMode: health?.authMode === "direct",
  };
}

function ssoButtonClass() {
  return "flex h-[52px] w-full items-center justify-center gap-2.5 rounded-lg border border-border bg-background text-[15px] font-medium text-foreground transition-colors hover:bg-accent";
}

export function GoogleButton() {
  return (
    <button
      type="button"
      className={ssoButtonClass()}
      onClick={() => signIn("google", { callbackUrl: "/", redirect: true })}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
        <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z" />
        <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.93v2.33A9 9 0 0 0 9 18Z" />
        <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.93a9 9 0 0 0 0 8.1l3.04-2.33Z" />
        <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.46 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .93 4.95l3.04 2.33C4.68 5.16 6.66 3.58 9 3.58Z" />
      </svg>
      <span>Google</span>
    </button>
  );
}

export function MicrosoftButton() {
  return (
    <button
      type="button"
      className={ssoButtonClass()}
      onClick={() => signIn("microsoft", { callbackUrl: "/", redirect: true })}
    >
      <svg width="17" height="17" viewBox="0 0 23 23" aria-hidden="true">
        <path fill="#F25022" d="M0 0h11v11H0z" />
        <path fill="#7FBA00" d="M12 0h11v11H12z" />
        <path fill="#00A4EF" d="M0 12h11v11H0z" />
        <path fill="#FFB900" d="M12 12h11v11H12z" />
      </svg>
      <span>Microsoft</span>
    </button>
  );
}

export function SsoDivider() {
  return (
    <div className="my-7 flex items-center gap-3.5">
      <div className="h-px flex-1 bg-border" />
      <span className="text-xs text-muted-foreground">or continue with</span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
