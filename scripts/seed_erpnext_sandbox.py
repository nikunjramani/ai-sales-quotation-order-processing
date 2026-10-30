"""Prepare the local ERPNext sandbox (infra/erpnext/compose.yaml) with synthetic data.

Run after `docker compose -p quotation-erpnext -f infra/erpnext/compose.yaml up -d` once the
site answers http://localhost:8090/api/method/ping:

    uv run python scripts/seed_erpnext_sandbox.py

It completes the setup wizard (company "Pilot Sandbox", INR), creates an item group with three
items, prices in "Standard Selling", a stock receipt into "Stores - PS" and a customer, then
prints an API key and secret for the Administrator. Everything is synthetic; run it again
safely (existing records are kept). Never point it at a real ERPNext.
"""

import argparse
import json
import sys
from datetime import date
from typing import Any

import httpx

COMPANY = "Pilot Sandbox"
ABBR = "PS"
WAREHOUSE = f"Stores - {ABBR}"
GROUP = "Pumps and Cables"
CUSTOMER = "Sandbox Customer"
ITEMS = (
    # code, name, unit, rate, stock
    ("PUMP-100", "Centrifugal pump 100 L/min", "Nos", "4250.00", "12"),
    ("CABLE-2C", "2-core power cable", "Meter", "38.50", "500"),
    ("FAN-400", "Exhaust fan 400 mm", "Nos", "2150.00", "0"),
)


class Sandbox:
    def __init__(self, base: str, password: str) -> None:
        self.http = httpx.Client(base_url=base, timeout=120)
        response = self.http.post(
            "/api/method/login", data={"usr": "Administrator", "pwd": password}
        )
        response.raise_for_status()

    def call(self, method: str, **params: Any) -> Any:
        response = self.http.post(f"/api/method/{method}", data=params)
        if response.status_code != 200:
            raise RuntimeError(f"{method}: HTTP {response.status_code} {response.text[:500]}")
        return response.json().get("message")

    def exists(self, doctype: str, name: str) -> bool:
        return self.http.get(f"/api/resource/{doctype}/{name}").status_code == 200

    def insert(self, doctype: str, document: dict[str, Any]) -> dict[str, Any]:
        response = self.http.post(f"/api/resource/{doctype}", json=document)
        if response.status_code != 200:
            raise RuntimeError(f"{doctype}: HTTP {response.status_code} {response.text[:800]}")
        data: dict[str, Any] = response.json()["data"]
        return data

    def ensure(self, doctype: str, name: str, document: dict[str, Any]) -> None:
        if not self.exists(doctype, name):
            self.insert(doctype, document)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8090")
    parser.add_argument("--password", default="admin")
    arguments = parser.parse_args()
    if "localhost" not in arguments.base_url and "127.0.0.1" not in arguments.base_url:
        sys.exit("Only a local sandbox may be seeded")
    erp = Sandbox(arguments.base_url, arguments.password)

    if not erp.exists("Company", COMPANY):
        today = date.today()
        start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        erp.call(
            "frappe.desk.page.setup_wizard.setup_wizard.setup_complete",
            args=json.dumps(
                {
                    "language": "English",
                    "country": "India",
                    "timezone": "Asia/Kolkata",
                    "currency": "INR",
                    "full_name": "Sandbox Admin",
                    "email": "admin@sandbox.example",
                    "company_name": COMPANY,
                    "company_abbr": ABBR,
                    "chart_of_accounts": "Standard",
                    "fy_start_date": start.isoformat(),
                    "fy_end_date": date(start.year + 1, 3, 31).isoformat(),
                    "setup_demo": 0,
                }
            ),
        )
    erp.ensure(
        "Item Group",
        GROUP,
        {"item_group_name": GROUP, "parent_item_group": "All Item Groups", "is_group": 0},
    )
    for code, name, unit, rate, _ in ITEMS:
        erp.ensure(
            "Item",
            code,
            {
                "item_code": code,
                "item_name": name,
                "item_group": GROUP,
                "stock_uom": unit,
                "is_stock_item": 1,
                "is_sales_item": 1,
                "valuation_rate": rate,
            },
        )
        prices = erp.http.get(
            "/api/resource/Item Price",
            params={
                "filters": json.dumps(
                    [["item_code", "=", code], ["price_list", "=", "Standard Selling"]]
                )
            },
        ).json()["data"]
        if not prices:
            erp.insert(
                "Item Price",
                {"item_code": code, "price_list": "Standard Selling", "price_list_rate": rate},
            )
    receipts = erp.http.get(
        "/api/resource/Stock Entry",
        params={"filters": json.dumps([["remarks", "=", "Sandbox opening stock"]])},
    ).json()["data"]
    if not receipts:
        erp.insert(
            "Stock Entry",
            {
                "stock_entry_type": "Material Receipt",
                "company": COMPANY,
                "remarks": "Sandbox opening stock",
                "docstatus": 1,
                "items": [
                    {"item_code": code, "qty": stock, "t_warehouse": WAREHOUSE, "basic_rate": rate}
                    for code, _, _, rate, stock in ITEMS
                    if stock != "0"
                ],
            },
        )
    erp.ensure(
        "Customer",
        CUSTOMER,
        {"customer_name": CUSTOMER, "customer_type": "Company", "customer_group": "Commercial"},
    )
    secret = erp.call("frappe.core.doctype.user.user.generate_keys", user="Administrator")
    key = erp.http.get("/api/resource/User/Administrator").json()["data"]["api_key"]
    print(json.dumps({"api_key": key, "api_secret": secret["api_secret"]}, indent=2))
    print(
        f"Enable ERPNext in the portal with address {arguments.base_url}, price list "
        f"'Standard Selling', warehouse '{WAREHOUSE}', customer '{CUSTOMER}'."
    )


if __name__ == "__main__":
    main()
