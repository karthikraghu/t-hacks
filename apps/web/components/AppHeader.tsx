import Link from "next/link";
import type { ReactNode } from "react";

interface Props {
  /** The progress rail for whichever tool is mounted, or nothing on the front page. */
  children?: ReactNode;
}

export function AppHeader({ children }: Props) {
  return (
    <header className="header">
      <div className="header-inner">
        <Link className="brand" href="/">
          <span aria-hidden="true" className="brand-mark" />
          <span className="brand-name">Klarblick</span>
        </Link>
        {children}
      </div>
    </header>
  );
}
