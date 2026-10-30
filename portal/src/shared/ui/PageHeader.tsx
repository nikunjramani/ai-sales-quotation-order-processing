import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  title: ReactNode;
  /** One plain sentence: what this page is for, so a first-time visitor knows what to do. */
  hint?: ReactNode;
  icon?: LucideIcon;
  /** Buttons shown next to the title (for example "Add product"). */
  actions?: ReactNode;
}

/** The title block every page starts with: an icon, the page name and a one-line hint. */
export function PageHeader({ title, hint, icon: Icon, actions }: Props) {
  return (
    <header className="page-header">
      <div className="page-title">
        {Icon && (
          <span className="page-icon" aria-hidden="true">
            <Icon size={26} />
          </span>
        )}
        <div>
          <h1>{title}</h1>
          {hint && <p className="hint">{hint}</p>}
        </div>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
