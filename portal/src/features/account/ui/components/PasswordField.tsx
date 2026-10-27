import { useId, useState } from "react";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** "new-password" lets password managers offer a strong one; "current-password" fills it. */
  autoComplete: "new-password" | "current-password";
  hints?: string[];
}

export function PasswordField({ label, value, onChange, autoComplete, hints = [] }: Props) {
  const id = useId();
  const [shown, setShown] = useState(false);
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type={shown ? "text" : "password"}
        value={value}
        autoComplete={autoComplete}
        maxLength={128}
        required
        onChange={(event) => onChange(event.target.value)}
      />
      <button type="button" className="secondary small" onClick={() => setShown(!shown)}>
        {shown ? "Hide" : "Show"}
      </button>
      {hints.map((hint) => (
        <p key={hint} className="muted small">
          {hint}
        </p>
      ))}
    </>
  );
}
