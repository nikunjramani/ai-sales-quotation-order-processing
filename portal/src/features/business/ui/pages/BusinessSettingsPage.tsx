import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

import { useDetailsForm, usePdfDetailsForm } from "../../hooks/useBusinessForms";
import { useBusinessSettings, useLogo } from "../../hooks/useBusiness";
import type { BusinessSettings } from "../../model/types";
import { timeZones } from "../../services/regions";
import { SettingsNav } from "../components/SettingsNav";

export function BusinessSettingsPage() {
  const settings = useBusinessSettings();
  return (
    <section>
      <h1>Settings</h1>
      <SettingsNav />
      <QueryState isLoading={settings.isLoading} error={settings.error}>
        {settings.data && (
          // key: the forms start again from the saved values after each reload.
          <Forms key={settings.data.profile.version + settings.data.name} settings={settings.data} />
        )}
      </QueryState>
    </section>
  );
}

function Forms({ settings }: { settings: BusinessSettings }) {
  const details = useDetailsForm(settings);
  const pdf = usePdfDetailsForm(settings);
  const logo = useLogo();
  return (
    <>
      <h2>Business</h2>
      <form className="card" onSubmit={details.submit}>
        <label htmlFor="details-name">Business name</label>
        <input
          id="details-name"
          required
          maxLength={200}
          value={details.name}
          onChange={(event) => details.setName(event.target.value)}
        />
        <label htmlFor="details-country">Country (two-letter code)</label>
        <input
          id="details-country"
          required
          maxLength={2}
          value={details.country}
          onChange={(event) => details.setCountry(event.target.value)}
        />
        {details.countryLabel && <p className="muted small">{details.countryLabel}</p>}
        <label htmlFor="details-time-zone">Time zone</label>
        <select
          id="details-time-zone"
          value={details.timeZone}
          onChange={(event) => details.setTimeZone(event.target.value)}
        >
          {timeZones().map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
        <ErrorMessage message={details.error} />
        {details.saved && <p className="muted small">Saved.</p>}
        <button type="submit" disabled={details.busy}>
          Save
        </button>
      </form>

      <h2>On your quotations</h2>
      <form className="card" onSubmit={pdf.submit}>
        <p className="muted small">
          Printed at the top of every quotation PDF. Quotations already sent keep the details
          they were made with.
        </p>
        <label htmlFor="pdf-legal-name">Legal name</label>
        <input
          id="pdf-legal-name"
          maxLength={200}
          value={pdf.legalName}
          onChange={(event) => pdf.setLegalName(event.target.value)}
        />
        <label htmlFor="pdf-address">Address (up to 4 lines)</label>
        <textarea
          id="pdf-address"
          rows={4}
          maxLength={500}
          value={pdf.address}
          onChange={(event) => pdf.setAddress(event.target.value)}
        />
        <label htmlFor="pdf-tax-label">Tax ID name (optional, e.g. GSTIN or VAT no.)</label>
        <input
          id="pdf-tax-label"
          maxLength={32}
          value={pdf.taxLabel}
          onChange={(event) => pdf.setTaxLabel(event.target.value)}
        />
        <label htmlFor="pdf-tax-id">Tax ID (optional)</label>
        <input
          id="pdf-tax-id"
          maxLength={64}
          value={pdf.taxId}
          onChange={(event) => pdf.setTaxId(event.target.value)}
        />
        <ErrorMessage message={pdf.error} />
        {pdf.saved && <p className="muted small">Saved.</p>}
        <button type="submit" disabled={pdf.busy}>
          Save
        </button>
      </form>

      <h2>Logo (optional)</h2>
      <div className="card">
        {settings.profile.has_logo && (
          <img
            src={logo.url(settings.profile.version)}
            alt="Current logo"
            style={{ maxWidth: "240px", maxHeight: "96px" }}
          />
        )}
        <label htmlFor="logo-file">PNG or JPEG, at most 1 MB</label>
        <input
          id="logo-file"
          type="file"
          accept="image/png,image/jpeg"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) logo.upload.mutate(file);
          }}
        />
        <ErrorMessage message={logo.upload.error?.message ?? logo.remove.error?.message} />
        {settings.profile.has_logo && (
          <button
            className="danger"
            disabled={logo.remove.isPending}
            onClick={() => logo.remove.mutate()}
          >
            Remove logo
          </button>
        )}
      </div>
    </>
  );
}
