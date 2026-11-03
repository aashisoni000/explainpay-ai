import { Suspense } from "react";
import { WorkspaceShell } from "@/components/workspace/shell";
import { Loading } from "@/components/workspace/ui";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Loading />}><WorkspaceShell>{children}</WorkspaceShell></Suspense>;
}
