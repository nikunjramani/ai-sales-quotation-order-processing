import { Link } from "react-router";

import type { ProductSummary } from "../../model/types";
import { priceLine, stockLine } from "../../services/priceService";

export function ProductTable({ products }: { products: ProductSummary[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Name</th>
            <th>Category</th>
            <th>Price (excl. tax)</th>
            <th>Stock</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.product_id}>
              <td>
                <Link to={`/catalogue/${product.product_id}`}>{product.sku}</Link>
                {product.archived_at && <span className="badge"> Archived</span>}
              </td>
              <td>{product.name}</td>
              <td>{product.category?.name ?? "—"}</td>
              <td>
                {product.current_price ? (
                  priceLine(product.current_price)
                ) : (
                  <span className="badge warn">No price</span>
                )}
              </td>
              <td>
                {product.stock ? stockLine(product.stock) : <span className="muted">No count</span>}
                {product.stock?.stale && <span className="badge warn"> Old count</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
