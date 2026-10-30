import { FileText } from "lucide-react";
import { useSearchParams } from "react-router";

import { PageHeader } from "@/shared/ui/PageHeader";
import { FilterTabs } from "@/shared/ui/FilterTabs";
import { QueryState } from "@/shared/ui/QueryState";

import { useQuotationList } from "../../hooks/useQuotations";
import { QUOTATION_FILTERS, filterById } from "../../services/quotationService";
import { QuotationRow } from "../components/QuotationRow";

export function QuotationListPage() {
  // The filter lives in the URL (?filter=revision), so it survives refresh and can be shared.
  const [params, setParams] = useSearchParams();
  const filter = filterById(params.get("filter"));
  const list = useQuotationList(filter.statuses);

  return (
    <section>
      <PageHeader
        icon={FileText}
        title="Quotes"
        hint="A quote tells a customer what things cost. Check each one, then approve it so it can be sent."
      />
      <FilterTabs tabs={QUOTATION_FILTERS} selected={filter.id} onSelect={(id) => setParams({ filter: id })} />
      <QueryState isLoading={list.isLoading} error={list.error} isEmpty={list.data?.length === 0}>
        <ul className="list">
          {list.data?.map((item) => <QuotationRow key={item.quotation_id} item={item} />)}
        </ul>
      </QueryState>
    </section>
  );
}
