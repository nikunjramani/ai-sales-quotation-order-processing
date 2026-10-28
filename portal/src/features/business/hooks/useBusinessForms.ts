import { useState, type FormEvent } from "react";

import type { BusinessSettings, PricingPolicy, RoundingMode } from "../model/types";
import {
  fractionToPercent,
  percentToFraction,
  SUGGESTED,
  suggestedMinorUnits,
} from "../services/pricingForm";
import { browserTimeZone, countryName } from "../services/regions";
import { useCreateBusiness, useUpdateDetails, useUpdatePricing, useUpdateProfile } from "./useBusiness";
import { useInvite } from "./useMembers";

/** Create a business (Q14/Q15): currency and tax rate may each be left for later. */
export function useCreateBusinessForm() {
  const create = useCreateBusiness();
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [timeZone, setTimeZone] = useState(browserTimeZone);
  const [validity, setValidity] = useState("7");
  const [currency, setCurrency] = useState("");
  const [taxPercent, setTaxPercent] = useState("");
  const upperCountry = country.trim().toUpperCase();
  const tax = taxPercent.trim() === "" ? null : percentToFraction(taxPercent);
  const problem =
    countryName(upperCountry) === null
      ? "Enter a two-letter country code, e.g. IN or DE."
      : taxPercent.trim() !== "" && tax === null
        ? "Tax rate: a percentage below 100 with at most 4 decimals."
        : null;
  return {
    name,
    setName,
    country,
    setCountry,
    countryLabel: countryName(upperCountry),
    timeZone,
    setTimeZone,
    validity,
    setValidity,
    currency,
    setCurrency,
    taxPercent,
    setTaxPercent,
    problem: country ? problem : null,
    submit(event: FormEvent) {
      event.preventDefault();
      if (problem) return;
      create.mutate({
        name,
        country: upperCountry,
        time_zone: timeZone,
        quote_validity_days: Number(validity) || 7,
        pricing: { currency: currency.trim().toUpperCase() || null, tax_rate: tax },
      });
    },
    busy: create.isPending,
    error: create.error?.message ?? null,
  };
}

export function useDetailsForm(settings: BusinessSettings) {
  const update = useUpdateDetails();
  const [name, setName] = useState(settings.name);
  const [country, setCountry] = useState(settings.country ?? "");
  const [timeZone, setTimeZone] = useState(settings.time_zone ?? browserTimeZone());
  return {
    name,
    setName,
    country,
    setCountry,
    countryLabel: countryName(country.trim().toUpperCase()),
    timeZone,
    setTimeZone,
    submit(event: FormEvent) {
      event.preventDefault();
      update.mutate({ name, country: country.trim().toUpperCase(), time_zone: timeZone });
    },
    busy: update.isPending,
    saved: update.isSuccess,
    error: update.error?.message ?? null,
  };
}

export function usePdfDetailsForm(settings: BusinessSettings) {
  const update = useUpdateProfile();
  const profile = settings.profile;
  const [legalName, setLegalName] = useState(profile.legal_name ?? "");
  const [address, setAddress] = useState(profile.address ?? "");
  const [taxLabel, setTaxLabel] = useState(profile.tax_id_label ?? "");
  const [taxId, setTaxId] = useState(profile.tax_id ?? "");
  const empty = (value: string) => (value.trim() === "" ? null : value);
  return {
    legalName,
    setLegalName,
    address,
    setAddress,
    taxLabel,
    setTaxLabel,
    taxId,
    setTaxId,
    submit(event: FormEvent) {
      event.preventDefault();
      update.mutate({
        legal_name: empty(legalName),
        address: empty(address),
        tax_id_label: empty(taxLabel),
        tax_id: empty(taxId),
        expected_version: profile.version,
      });
    },
    busy: update.isPending,
    saved: update.isSuccess,
    error: update.error?.message ?? null,
  };
}

/** Every field must be saved by the manager; suggestions are shown, never stored silently. */
export function usePricingForm(policy: PricingPolicy) {
  const update = useUpdatePricing();
  const [currency, setCurrency] = useState(policy.currency ?? "");
  const [minorUnits, setMinorUnits] = useState(
    policy.minor_units === null ? "" : String(policy.minor_units),
  );
  const [rounding, setRounding] = useState<RoundingMode>(
    policy.rounding_mode ?? SUGGESTED.rounding_mode,
  );
  const [taxPercent, setTaxPercent] = useState(fractionToPercent(policy.tax_rate));
  const [priceMinutes, setPriceMinutes] = useState(
    String(
      policy.max_price_age_seconds === null
        ? SUGGESTED.max_price_age_minutes
        : policy.max_price_age_seconds / 60,
    ),
  );
  const [stockMinutes, setStockMinutes] = useState(
    String(
      policy.max_stock_age_seconds === null
        ? SUGGESTED.max_stock_age_minutes
        : policy.max_stock_age_seconds / 60,
    ),
  );
  const [validity, setValidity] = useState(String(policy.quote_validity_days));
  const upper = currency.trim().toUpperCase();
  const suggestion = suggestedMinorUnits(upper);
  const tax = percentToFraction(taxPercent);
  const problem =
    !/^[A-Z]{3}$/.test(upper)
      ? "Currency: a three-letter code, e.g. INR or EUR."
      : !/^[0-4]$/.test(minorUnits.trim())
        ? `Decimal places: 0 to 4${suggestion === null ? "" : ` (usual for ${upper}: ${suggestion})`}.`
        : tax === null
          ? "Tax rate: a percentage below 100 with at most 4 decimals."
          : null;
  return {
    currency,
    setCurrency,
    minorUnits,
    setMinorUnits,
    suggestion,
    rounding,
    setRounding,
    taxPercent,
    setTaxPercent,
    priceMinutes,
    setPriceMinutes,
    stockMinutes,
    setStockMinutes,
    validity,
    setValidity,
    complete: policy.complete,
    problem,
    submit(event: FormEvent) {
      event.preventDefault();
      if (problem || tax === null) return;
      update.mutate({
        currency: upper,
        minor_units: Number(minorUnits.trim()),
        rounding_mode: rounding,
        tax_rate: tax,
        max_price_age_seconds: Math.round(Number(priceMinutes) * 60),
        max_stock_age_seconds: Math.round(Number(stockMinutes) * 60),
        quote_validity_days: Number(validity),
        expected_version: policy.version,
      });
    },
    busy: update.isPending,
    saved: update.isSuccess,
    error: update.error?.message ?? null,
  };
}

export function useInviteForm() {
  const invite = useInvite();
  const [email, setEmail] = useState("");
  const [roles, setRoles] = useState<string[]>(["sales_operator"]);
  return {
    email,
    setEmail,
    roles,
    setRoles,
    submit(event: FormEvent) {
      event.preventDefault();
      invite.mutate({ email, roles }, { onSuccess: () => setEmail("") });
    },
    busy: invite.isPending,
    sent: invite.isSuccess,
    error: invite.error?.message ?? null,
  };
}
