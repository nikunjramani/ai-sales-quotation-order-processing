import { Link } from "react-router";

import { useCurrentTenant } from "@/features/tenant";

/** Reminds everyone that a business in setup does not contact customers yet (D3, Q11). */
export function StatusBanner() {
  const { tenant, can } = useCurrentTenant();
  if (tenant?.status === "setting_up") {
    return (
      <p className="notice">
        {tenant.name} is being set up: nothing is sent to customers yet.{" "}
        {can("tenant:manage") && <Link to="/setup">Finish the setup</Link>}
      </p>
    );
  }
  if (tenant?.status === "suspended") {
    return (
      <p className="notice">
        {tenant.name} is suspended: nothing can be changed and nothing is sent.
      </p>
    );
  }
  return null;
}
