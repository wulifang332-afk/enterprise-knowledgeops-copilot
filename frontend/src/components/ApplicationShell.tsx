import type { ReactNode } from "react";

import { ContentContainer } from "./ContentContainer";
import { Header } from "./Header";

type ApplicationShellProps = {
  children: ReactNode;
};

export function ApplicationShell({ children }: ApplicationShellProps) {
  return (
    <div className="app-shell">
      <Header />
      <ContentContainer>{children}</ContentContainer>
    </div>
  );
}
