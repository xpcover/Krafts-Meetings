"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface OnboardingFieldProps extends React.ComponentProps<"input"> {
  id: string;
  label: string;
  /** Rendered to the right of the label, e.g. a "Forgot?" link. */
  action?: React.ReactNode;
}

/**
 * Label + input at the 52px touch height the mobile screens use, built on the
 * dashboard's own Input so focus, invalid and disabled states stay identical.
 */
export function OnboardingField({
  id,
  label,
  action,
  className,
  ...props
}: OnboardingFieldProps) {
  return (
    <div className="flex flex-col gap-[7px]">
      <div className="flex items-center justify-between">
        <Label htmlFor={id} className="text-[13px] font-medium text-muted-foreground">
          {label}
        </Label>
        {action}
      </div>
      <Input
        id={id}
        className={cn("h-[52px] rounded-lg px-3.5 text-base md:text-base", className)}
        {...props}
      />
    </div>
  );
}
