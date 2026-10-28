import { useNavigate } from "react-router";

import { useCurrentTenant } from "../hooks/useCurrentTenant";

export function TenantSwitcher() {
  const { tenant, tenants, selectTenant } = useCurrentTenant();
  const navigate = useNavigate();
  if (tenants.length <= 1) return <span>{tenant?.name}</span>;
  return (
    <select
      aria-label="Business"
      value={tenant?.tenant_id ?? ""}
      onChange={(event) => {
        selectTenant(event.target.value);
        navigate("/");
      }}
    >
      {tenants.map((item) => (
        <option key={item.tenant_id} value={item.tenant_id}>
          {item.name}
        </option>
      ))}
    </select>
  );
}
