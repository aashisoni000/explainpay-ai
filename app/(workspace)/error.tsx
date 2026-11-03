"use client";
import { ErrorNotice } from "@/components/workspace/ui";
export default function WorkspaceError({ reset }: { reset: () => void }) {
  return <ErrorNotice error="This workspace view could not be loaded. Please retry." retry={reset} />;
}
