import { Link, useNavigate, useParams } from "react-router";

import { useCanEditCatalogue, useCatalogueSummary, useProduct } from "../../hooks/useCatalogue";
import { ArchiveControls } from "../components/ArchiveControls";
import { CatalogueSourceBanner } from "../components/CatalogueSourceBanner";
import { ChangeHistory } from "../components/ChangeHistory";
import { PricePanel } from "../components/PricePanel";
import { ProductFormCard } from "../components/ProductFormCard";
import { StockPanel } from "../components/StockPanel";
import { QueryState } from "@/shared/ui/QueryState";

/** A new product (#/catalogue/new) or one product with its prices, stock and changes. */
export function ProductPage() {
  const { productId } = useParams();
  const isNew = productId === undefined;
  const summary = useCatalogueSummary();
  const product = useProduct(productId);
  const canEdit = useCanEditCatalogue();
  const navigate = useNavigate();
  const units = summary.data?.units ?? [];
  return (
    <section>
      <p>
        <Link to="/catalogue">← Products</Link>
      </p>
      <h1>{isNew ? "Add product" : (product.data?.sku ?? "Product")}</h1>
      {summary.data && <CatalogueSourceBanner summary={summary.data} />}
      {isNew ? (
        <QueryState isLoading={summary.isLoading} error={summary.error}>
          {summary.data && (
            <ProductFormCard
              units={units}
              product={null}
              editable={canEdit}
              onSaved={(saved) => navigate(`/catalogue/${saved.product_id}`, { replace: true })}
            />
          )}
        </QueryState>
      ) : (
        <QueryState isLoading={product.isLoading || summary.isLoading} error={product.error ?? summary.error}>
          {product.data && summary.data && (
            <>
              <ProductFormCard
                key={product.data.row_version}
                units={units}
                product={product.data}
                editable={canEdit && !product.data.archived_at}
                onSaved={() => undefined}
              />
              <PricePanel
                product={product.data}
                currency={summary.data.currency}
                timeZone={summary.data.time_zone}
                editable={canEdit}
              />
              <StockPanel
                product={product.data}
                maxStockAgeSeconds={summary.data.max_stock_age_seconds}
                editable={canEdit}
              />
              {canEdit && <ArchiveControls product={product.data} />}
              <ChangeHistory productId={product.data.product_id} />
            </>
          )}
        </QueryState>
      )}
    </section>
  );
}
