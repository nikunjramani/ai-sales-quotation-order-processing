import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { conversationRepository } from "../api/conversationRepository";

export const conversationKeys = {
  all: (tenantId: string) => ["tenants", tenantId, "conversations"] as const,
  inbox: (tenantId: string) => ["tenants", tenantId, "conversations", "inbox"] as const,
  one: (tenantId: string, id: string) => ["tenants", tenantId, "conversations", "one", id] as const,
  enquiry: (tenantId: string, id: string) =>
    ["tenants", tenantId, "conversations", "enquiry", id] as const,
  contacts: (tenantId: string, query: string) =>
    ["tenants", tenantId, "conversations", "contacts", query] as const,
  contact: (tenantId: string, id: string) =>
    ["tenants", tenantId, "conversations", "contact", id] as const,
  settings: (tenantId: string) => ["tenants", tenantId, "conversations", "settings"] as const,
};

const INBOX_REFRESH_MS = 15_000;

export function useInbox() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: conversationKeys.inbox(tenantId),
    queryFn: () => conversationRepository.inbox(tenantId),
    refetchInterval: INBOX_REFRESH_MS,
  });
}

export function useConversation(conversationId: string) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: conversationKeys.one(tenantId, conversationId),
    queryFn: () => conversationRepository.conversation(tenantId, conversationId),
    refetchInterval: INBOX_REFRESH_MS,
  });
}

export function useEnquiryMessages(enquiryId: string) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: conversationKeys.enquiry(tenantId, enquiryId),
    queryFn: () => conversationRepository.enquiryMessages(tenantId, enquiryId),
  });
}

export function useContacts(query: string) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: conversationKeys.contacts(tenantId, query),
    queryFn: () => conversationRepository.contacts(tenantId, query),
  });
}

export function useContact(contactId: string) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: conversationKeys.contact(tenantId, contactId),
    queryFn: () => conversationRepository.contact(tenantId, contactId),
  });
}

export function useMergeContact(contactId: string) {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (intoContactId: string) =>
      conversationRepository.merge(tenantId, contactId, intoContactId),
    onSettled: () => client.invalidateQueries({ queryKey: conversationKeys.all(tenantId) }),
  });
}

export function useCustomerMessages() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: conversationKeys.settings(tenantId),
    queryFn: () => conversationRepository.customerMessages(tenantId),
  });
  const save = useMutation({
    mutationFn: (acknowledge: boolean) =>
      conversationRepository.setCustomerMessages(tenantId, { acknowledge_enquiries: acknowledge }),
    onSettled: () => client.invalidateQueries({ queryKey: conversationKeys.settings(tenantId) }),
  });
  return { query, save };
}

/** Send a failed customer message again; the conversation reloads to show the new one. */
export function useResendMessage() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) => conversationRepository.resend(tenantId, messageId),
    onSettled: () => client.invalidateQueries({ queryKey: conversationKeys.all(tenantId) }),
  });
}
