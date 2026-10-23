import { dateTime } from "@/shared/lib/format";

import type { Delivery } from "../../model/types";
import { DELIVERY_STATUS, channelLabel, needsAttention } from "../../services/deliveryService";

export function DeliveryList({ deliveries }: { deliveries: Delivery[] }) {
  if (!deliveries.length) return <p className="muted">Preparing the delivery…</p>;
  return (
    <ul className="list">
      {deliveries.map((delivery) => {
        const view = DELIVERY_STATUS[delivery.status];
        return (
          <li key={delivery.delivery_id} className="row static deliveries">
            <div>
              <strong>{channelLabel(delivery.channel)}</strong>{" "}
              <span className="muted small">{delivery.recipient}</span>
              <div className="small muted">
                Version {delivery.version}
                {delivery.delivered_at && <> · delivered {dateTime(delivery.delivered_at)}</>}
                {delivery.first_downloaded_at && (
                  <> · customer downloaded {dateTime(delivery.first_downloaded_at)}</>
                )}
              </div>
              {needsAttention(delivery) && delivery.last_error && (
                <p className="error small" role="alert">
                  {delivery.last_error}
                </p>
              )}
              {view.help && <p className="small muted">{view.help}</p>}
            </div>
            <span className={`badge ${view.tone}`}>{view.label}</span>
          </li>
        );
      })}
    </ul>
  );
}
