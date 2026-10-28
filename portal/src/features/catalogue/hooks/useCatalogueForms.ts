import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { useTenantId } from "@/features/tenant";
import { isApiError } from "@/shared/api/httpClient";
import { newCommandId } from "@/shared/lib/commandId";

import { catalogueRepository } from "../api/catalogueRepository";
import type { FieldProblem, Product, ProductForm } from "../model/types";
import { checkPriceText, checkStockText, pricePayload, stockPayload } from "../services/priceService";
import {
  checkProductForm,
  conflictCodeFrom,
  emptyProductForm,
  fieldProblemFrom,
  formFromProduct,
  hasChanges,
  toCreatePayload,
  toPatchPayload,
} from "../services/productFormService";
import { useRefreshCatalogue } from "./useCatalogue";

/** A server error as something to show: a field problem (422) or a message. */
function problemFrom(error: unknown): { field: FieldProblem | null; message: string | null } {
  if (!error) return { field: null, message: null };
  if (isApiError(error, 422)) {
    const field = fieldProblemFrom(error.detail);
    if (field) return { field, message: null };
  }
  if (isApiError(error, 409) && conflictCodeFrom(error.detail) === "version_conflict") {
    return { field: null, message: "Someone else changed this product. Reload the page to see it." };
  }
  return { field: null, message: error instanceof Error ? error.message : "Something went wrong" };
}

/** New product (no `product`) or edit. `onSaved` gets the saved product. */
export function useProductForm(
  units: readonly string[],
  product: Product | null,
  onSaved: (saved: Product) => void,
) {
  const tenantId = useTenantId();
  const refresh = useRefreshCatalogue();
  const [form, setForm] = useState<ProductForm>(() =>
    product ? formFromProduct(product) : emptyProductForm(units),
  );
  const [touched, setTouched] = useState(false);
  const save = useMutation({
    mutationFn: () =>
      product
        ? catalogueRepository.updateProduct(tenantId, product.product_id, toPatchPayload(form, product))
        : catalogueRepository.createProduct(tenantId, toCreatePayload(form)),
    onSuccess: (saved) => {
      void refresh();
      onSaved(saved);
    },
  });
  const local = touched ? checkProductForm(form, units, product === null) : null;
  const server = problemFrom(save.error);
  const unchanged = product !== null && !hasChanges(toPatchPayload(form, product));
  return {
    form,
    set: (field: keyof ProductForm, value: string) => {
      setTouched(true);
      setForm((current) => ({ ...current, [field]: value }));
    },
    problem: local ?? server.field,
    error: server.message,
    unchanged,
    busy: save.isPending,
    submit(event: FormEvent) {
      event.preventDefault();
      setTouched(true);
      if (checkProductForm(form, units, product === null) || unchanged) return;
      save.mutate();
    },
  };
}

export function usePriceForm(productId: string, timeZone: string | null) {
  const tenantId = useTenantId();
  const refresh = useRefreshCatalogue();
  const [amount, setAmount] = useState("");
  const [startDate, setStartDate] = useState<string | null>(null);
  const [note, setNote] = useState("");
  // One request ID per entry: a retry after a lost answer is not stored twice.
  const [commandId, setCommandId] = useState(newCommandId);
  const add = useMutation({
    mutationFn: () =>
      catalogueRepository.addPrice(tenantId, productId, pricePayload(amount, startDate, timeZone, note, commandId)),
    onSuccess: () => {
      setAmount("");
      setNote("");
      setStartDate(null);
      setCommandId(newCommandId());
      void refresh();
    },
  });
  const local = amount ? checkPriceText(amount) : null;
  const server = problemFrom(add.error);
  return {
    amount,
    setAmount,
    startDate,
    setStartDate,
    note,
    setNote,
    problem: local ?? server.field?.message ?? null,
    error: server.message,
    busy: add.isPending,
    saved: add.isSuccess,
    submit(event: FormEvent) {
      event.preventDefault();
      if (checkPriceText(amount)) return;
      add.mutate();
    },
  };
}

export function useStockForm(productId: string) {
  const tenantId = useTenantId();
  const refresh = useRefreshCatalogue();
  const [quantity, setQuantity] = useState("");
  const [notTracked, setNotTracked] = useState(false);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [commandId, setCommandId] = useState(newCommandId);
  const add = useMutation({
    mutationFn: () =>
      catalogueRepository.addStock(tenantId, productId, stockPayload(quantity, notTracked, asOf, note, commandId)),
    onSuccess: () => {
      setQuantity("");
      setNote("");
      setAsOf(null);
      setCommandId(newCommandId());
      void refresh();
    },
  });
  const local = quantity || notTracked ? checkStockText(quantity, notTracked) : null;
  const server = problemFrom(add.error);
  return {
    quantity,
    setQuantity,
    notTracked,
    setNotTracked,
    asOf,
    setAsOf,
    note,
    setNote,
    problem: local ?? server.field?.message ?? null,
    error: server.message,
    busy: add.isPending,
    saved: add.isSuccess,
    submit(event: FormEvent) {
      event.preventDefault();
      if (checkStockText(quantity, notTracked)) return;
      add.mutate();
    },
  };
}

export function useCategoryForms() {
  const tenantId = useTenantId();
  const refresh = useRefreshCatalogue();
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: () => catalogueRepository.createCategory(tenantId, name.trim()),
    onSuccess: () => {
      setName("");
      void refresh();
    },
  });
  const update = useMutation({
    mutationFn: (change: { categoryId: string; name?: string; archived?: boolean; version: number }) =>
      catalogueRepository.updateCategory(tenantId, change.categoryId, {
        name: change.name,
        archived: change.archived,
        expected_version: change.version,
      }),
    onSettled: refresh,
  });
  return {
    name,
    setName,
    create,
    update,
    error: problemFrom(create.error ?? update.error),
    submit(event: FormEvent) {
      event.preventDefault();
      if (name.trim()) create.mutate();
    },
  };
}
