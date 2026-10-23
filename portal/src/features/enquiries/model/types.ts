export interface EnquirySummary {
  enquiry_id: string;
  channel: string;
  status: string;
  customer_reference: string | null;
  received_at: string;
  preview: string;
}
