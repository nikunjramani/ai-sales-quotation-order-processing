import { UserRoundSearch } from "lucide-react";
import { useSearchParams } from "react-router";

import { PageHeader } from "@/shared/ui/PageHeader";
import { dateTime } from "@/shared/lib/format";
import { FilterTabs } from "@/shared/ui/FilterTabs";
import { QueryState } from "@/shared/ui/QueryState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import { useEnquiryList } from "../../hooks/useEnquiries";
import { ENQUIRY_FILTERS, enquiryFilterById } from "../../services/enquiryService";

/** Exception view: enquiries the system could not turn into a quotation on its own. */
export function EnquiryListPage() {
  const [params, setParams] = useSearchParams();
  const filter = enquiryFilterById(params.get("filter"));
  const list = useEnquiryList(filter.statuses);

  return (
    <section>
      <PageHeader
        icon={UserRoundSearch}
        title="Customer requests"
        hint="What customers asked for. Most become quotes by themselves; the ones here need a person to look."
      />
      <FilterTabs tabs={ENQUIRY_FILTERS} selected={filter.id} onSelect={(id) => setParams({ filter: id })} />
      <QueryState isLoading={list.isLoading} error={list.error} isEmpty={list.data?.length === 0}>
        <ul className="list">
          {list.data?.map((item) => (
            <li key={item.enquiry_id} className="row static">
              <span>
                <span className="quote">{item.preview}</span>
                <br />
                <span className="muted small">
                  {item.customer_reference ?? "No reference"} · {dateTime(item.received_at)}
                </span>
              </span>
              <StatusBadge status={item.status} />
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
