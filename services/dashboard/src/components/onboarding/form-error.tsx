import { AlertCircle } from "lucide-react";

export function FormError({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-lg bg-destructive/8 px-3.5 py-3"
    >
      <AlertCircle className="mt-px h-4 w-4 shrink-0 text-destructive" strokeWidth={1.7} />
      <span className="text-[13px] leading-snug text-destructive">{message}</span>
    </div>
  );
}
