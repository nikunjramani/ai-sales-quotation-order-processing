import { House, MapPinOff } from "lucide-react";
import { Link } from "react-router";

import { PageHeader } from "@/shared/ui/PageHeader";

export function NotFoundPage() {
  return (
    <section>
      <PageHeader icon={MapPinOff} title="Page not found" hint="This page does not exist. Let's go back home." />
      <Link className="button primary" to="/home">
        <House size={20} aria-hidden="true" />
        Go to Home
      </Link>
    </section>
  );
}
