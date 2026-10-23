import { ErrorMessage } from "@/shared/ui/QueryState";

import { useStartEnrollment } from "../../hooks/useChannels";

/**
 * Link a messaging account so review messages arrive there and can be answered in place.
 * Linking needs a one-time code sent from that account (proof that you control it).
 */
export function EnrollmentCard() {
  const enrollment = useStartEnrollment();
  const code = enrollment.data?.code;
  return (
    <div className="card">
      <p>
        Only a simulated channel exists so far (email and Telegram come later). Linking lets review
        messages reach that account and lets you approve from it.
      </p>
      <button className="primary" disabled={enrollment.isPending} onClick={() => enrollment.mutate("simulated")}>
        Link a simulated channel account
      </button>
      <ErrorMessage message={enrollment.error?.message} />
      {code && (
        <p className="notice">
          Send this code from the account within 10 minutes: <code>{code}</code>
          <br />
          <span className="small">
            Locally:{" "}
            <code>uv run python scripts/simulated_channel.py enroll --code {code} --user my-phone</code>
          </span>
        </p>
      )}
    </div>
  );
}
