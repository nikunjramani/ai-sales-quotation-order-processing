import { PEOPLE_ROLES, ROLE_LABEL, toggleRole } from "../../services/memberRules";

interface Props {
  roles: string[];
  onChange: (roles: string[]) => void;
  disabled?: boolean;
  name: string;
}

export function RoleCheckboxes({ roles, onChange, disabled = false, name }: Props) {
  return (
    <fieldset className="actions" disabled={disabled}>
      <legend className="small muted">Roles</legend>
      {PEOPLE_ROLES.map((role) => (
        <label key={role} className="small">
          <input
            type="checkbox"
            name={name}
            checked={roles.includes(role)}
            onChange={() => onChange(toggleRole(roles, role))}
          />{" "}
          {ROLE_LABEL[role]}
        </label>
      ))}
    </fieldset>
  );
}
