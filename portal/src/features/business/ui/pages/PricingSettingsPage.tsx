import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

import { usePricing } from "../../hooks/useBusiness";
import { usePricingForm } from "../../hooks/useBusinessForms";
import type { PricingPolicy, RoundingMode } from "../../model/types";
import { SettingsNav } from "../components/SettingsNav";

export function PricingSettingsPage() {
  const pricing = usePricing();
  return (
    <section>
      <h1>Settings</h1>
      <SettingsNav />
      <QueryState isLoading={pricing.isLoading} error={pricing.error}>
        {pricing.data && <PricingForm key={pricing.data.version} policy={pricing.data} />}
      </QueryState>
    </section>
  );
}

function PricingForm({ policy }: { policy: PricingPolicy }) {
  const form = usePricingForm(policy);
  return (
    <form className="card" onSubmit={form.submit}>
      {!form.complete && (
        <p className="notice">
          Not complete yet: quotations cannot be priced until every value below is saved. The
          pre-filled values are suggestions; check them before saving.
        </p>
      )}
      <label htmlFor="pricing-currency">Currency (e.g. INR)</label>
      <input
        id="pricing-currency"
        required
        maxLength={3}
        value={form.currency}
        onChange={(event) => form.setCurrency(event.target.value)}
      />
      <label htmlFor="pricing-minor">Decimal places in amounts (0 to 4)</label>
      <input
        id="pricing-minor"
        required
        inputMode="numeric"
        value={form.minorUnits}
        onChange={(event) => form.setMinorUnits(event.target.value)}
      />
      {form.suggestion !== null && (
        <p className="muted small">Usual for this currency: {form.suggestion}</p>
      )}
      <label htmlFor="pricing-rounding">Rounding</label>
      <select
        id="pricing-rounding"
        value={form.rounding}
        onChange={(event) => form.setRounding(event.target.value as RoundingMode)}
      >
        <option value="half_up">Half up (0.5 rounds up)</option>
        <option value="half_even">Half even (banker's rounding)</option>
      </select>
      <label htmlFor="pricing-tax">Tax rate in %</label>
      <input
        id="pricing-tax"
        required
        inputMode="decimal"
        value={form.taxPercent}
        onChange={(event) => form.setTaxPercent(event.target.value)}
      />
      <label htmlFor="pricing-price-age">Prices count as current for (minutes)</label>
      <input
        id="pricing-price-age"
        type="number"
        min={1}
        value={form.priceMinutes}
        onChange={(event) => form.setPriceMinutes(event.target.value)}
      />
      <label htmlFor="pricing-stock-age">Stock levels count as current for (minutes)</label>
      <input
        id="pricing-stock-age"
        type="number"
        min={1}
        value={form.stockMinutes}
        onChange={(event) => form.setStockMinutes(event.target.value)}
      />
      <label htmlFor="pricing-validity">Quotations stay valid for (days)</label>
      <input
        id="pricing-validity"
        type="number"
        min={1}
        value={form.validity}
        onChange={(event) => form.setValidity(event.target.value)}
      />
      <ErrorMessage message={form.problem ?? form.error} />
      {form.saved && <p className="muted small">Saved.</p>}
      <button type="submit" disabled={form.busy || Boolean(form.problem)}>
        Save pricing
      </button>
    </form>
  );
}
