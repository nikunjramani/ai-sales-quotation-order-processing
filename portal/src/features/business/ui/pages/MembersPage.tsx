import { useState } from "react";

import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

import { useInviteForm } from "../../hooks/useBusinessForms";
import {
  useChangeRoles,
  useInvitationActions,
  useInvitations,
  useMembers,
  useRemoveMember,
} from "../../hooks/useMembers";
import type { Member } from "../../model/types";
import { isLastAdministrator, ROLE_LABEL } from "../../services/memberRules";
import { RoleCheckboxes } from "../components/RoleCheckboxes";

/** Colleagues and invitations (administrators only, Q10). */
export function MembersPage() {
  const members = useMembers();
  const invitations = useInvitations();
  const actions = useInvitationActions();
  const invite = useInviteForm();
  return (
    <section>
      <h2>People</h2>
      <QueryState isLoading={members.isLoading} error={members.error}>
        <ul className="list">
          {(members.data ?? []).map((member) => (
            <MemberRow key={member.user_id} member={member} members={members.data ?? []} />
          ))}
        </ul>
      </QueryState>

      <h2>Invite someone</h2>
      <form className="card" onSubmit={invite.submit}>
        <label htmlFor="invite-email">Email</label>
        <input
          id="invite-email"
          type="email"
          required
          value={invite.email}
          onChange={(event) => invite.setEmail(event.target.value)}
        />
        <RoleCheckboxes name="invite-roles" roles={invite.roles} onChange={invite.setRoles} />
        <ErrorMessage message={invite.error} />
        {invite.sent && <p className="muted small">Invitation sent. The link works for 7 days.</p>}
        <button type="submit" disabled={invite.busy || invite.roles.length === 0}>
          Send invitation
        </button>
      </form>

      <h2>Invitations</h2>
      <QueryState
        isLoading={invitations.isLoading}
        error={invitations.error}
        isEmpty={invitations.data?.length === 0}
        emptyText="No invitations yet."
      >
        <ErrorMessage message={actions.resend.error?.message ?? actions.revoke.error?.message} />
        <ul className="list">
          {(invitations.data ?? []).map((item) => (
            <li key={item.invitation_id} className="row static">
              <span>
                <strong>{item.email}</strong> · {item.roles.map((r) => ROLE_LABEL[r] ?? r).join(", ")}
                <br />
                <span className="muted small">
                  {item.status} · email {item.email_status}
                </span>
              </span>
              {item.status === "pending" && (
                <span className="actions">
                  <button
                    className="secondary"
                    disabled={actions.resend.isPending}
                    onClick={() => actions.resend.mutate(item.invitation_id)}
                  >
                    Resend
                  </button>
                  <button
                    className="danger"
                    disabled={actions.revoke.isPending}
                    onClick={() => actions.revoke.mutate(item.invitation_id)}
                  >
                    Cancel
                  </button>
                </span>
              )}
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}

function MemberRow({ member, members }: { member: Member; members: Member[] }) {
  const [roles, setRoles] = useState(member.roles);
  const change = useChangeRoles();
  const remove = useRemoveMember();
  const last = isLastAdministrator(members, member);
  const changed = roles.join() !== member.roles.join();
  return (
    <li className="row static">
      <span>
        <strong>{member.display_name ?? member.email}</strong>
        {member.is_you && " (you)"}
        <br />
        <span className="muted small">{member.email}</span>
        <RoleCheckboxes
          name={`roles-${member.user_id}`}
          roles={roles}
          onChange={setRoles}
          disabled={change.isPending}
        />
        {last && <span className="muted small">The last administrator keeps that role.</span>}
        <ErrorMessage message={change.error?.message ?? remove.error?.message} />
      </span>
      <span className="actions">
        {changed && (
          <button
            className="primary"
            disabled={roles.length === 0 || (last && !roles.includes("administrator"))}
            onClick={() => change.mutate({ userId: member.user_id, roles })}
          >
            Save roles
          </button>
        )}
        {!last && !member.is_you && (
          <button
            className="danger"
            disabled={remove.isPending}
            onClick={() => remove.mutate(member.user_id)}
          >
            Remove
          </button>
        )}
      </span>
    </li>
  );
}
