import type { ReactNode } from "react";

type ContentContainerProps = {
  children: ReactNode;
};

export function ContentContainer({ children }: ContentContainerProps) {
  return <main className="content-container">{children}</main>;
}
