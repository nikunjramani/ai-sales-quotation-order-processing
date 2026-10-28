import { ErrorMessage } from "@/shared/ui/QueryState";

import { useCreateBusinessForm } from "../../hooks/useBusinessForms";
import { timeZones } from "../../services/regions";

export function CreateBusinessPage() {
  const form = useCreateBusinessForm();
  return (
    <section>
      <h1>Create your business</h1>
      <form className="card" onSubmit={form.submit}>
        <label htmlFor="business-name">Business name</label>
        <input
          id="business-name"
          required
          maxLength={200}
          value={form.name}
          onChange={(event) => form.setName(event.target.value)}
        />
        <label htmlFor="business-country">Country (two-letter code)</label>
        <input
          id="business-country"
          required
          maxLength={2}
          value={form.country}
          onChange={(event) => form.setCountry(event.target.value)}
        />
        {form.countryLabel && <p className="muted small">{form.countryLabel}</p>}
        <label htmlFor="business-time-zone">Time zone</label>
        <select
          id="business-time-zone"
          value={form.timeZone}
          onChange={(event) => form.setTimeZone(event.target.value)}
        >
          {timeZones().map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
        <label htmlFor="business-validity">Quotations stay valid for (days)</label>
        <input
          id="business-validity"
          type="number"
          min={1}
          value={form.validity}
          onChange={(event) => form.setValidity(event.target.value)}
        />
        <p className="muted small">
          Pricing: you can fill these now or later on the Pricing screen. Quotations can only be
          priced once every pricing value is saved.
        </p>
        <label htmlFor="business-currency">Currency (optional, e.g. INR)</label>
        <input
          id="business-currency"
          maxLength={3}
          value={form.currency}
          onChange={(event) => form.setCurrency(event.target.value)}
        />
        <label htmlFor="business-tax">Tax rate in % (optional, e.g. 18)</label>
        <input
          id="business-tax"
          inputMode="decimal"
          value={form.taxPercent}
          onChange={(event) => form.setTaxPercent(event.target.value)}
        />
        <ErrorMessage message={form.problem ?? form.error} />
        <button type="submit" disabled={form.busy || Boolean(form.problem)}>
          Create business
        </button>
      </form>
    </section>
  );
}
