# Copyright (c) 2023, connect and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	stock = get_total_stock(filters)

	return columns, stock


def get_columns():
	columns = [
		_("Company") + ":Link/Company:250",
		_("Warehouse") + ":Link/Warehouse:150",
		_("Item") + ":Link/Item:150",
		_("Description") + "::300",
		_("Current Qty") + ":Float:100",
		{
			"fieldname": "price_list_rate",
			"label": _("Price List Rate"),
			"fieldtype": "Currency",
			"width": "80"
		},
		{
			"fieldname": "total",
			"label": _("Total"),
			"fieldtype": "Currency",
			"width": "80"
		}
	] 
	return columns


def get_total_stock(filters):
	conditions = ""
	columns = ""

	if filters.get("group_by") == "Warehouse":
		if filters.get("company"):
			conditions += " AND warehouse.company = %s" % frappe.db.escape(
				filters.get("company"), percent=False
			) 
		if filters.get("price_list"):
			price_list = filters.get("price_list")
			conditions += " AND latest_price.price_list = %s" % frappe.db.escape(price_list)

		conditions += " GROUP BY ledger.warehouse, item.item_code"
		columns += "'' as company, ledger.warehouse"

	else:
		if filters.get("price_list"):
			price_list = filters.get("price_list")
			conditions += f' AND latest_price.price_list = "{price_list}"'

		conditions += " GROUP BY warehouse.company, item.item_code"
		columns += " warehouse.company, '' as warehouse"


	data = frappe.db.sql(
		"""
		SELECT
			{0},
			item.item_code,
			item.description,
			ledger.actual_qty as actual_qty,
			COALESCE(latest_price.price_list_rate, 0) as price_list_rate,
			(ledger.actual_qty * COALESCE(latest_price.price_list_rate, 0)) as total,
			latest_price.price_list
		FROM
			`tabBin` AS ledger
		INNER JOIN `tabItem` AS item
			ON ledger.item_code = item.item_code
		LEFT JOIN (
			SELECT
				item_code,
				MAX(valid_from) AS latest_valid_from
			FROM
				`tabItem Price`
			GROUP BY item_code
		) AS latest_valid
			ON item.item_code = latest_valid.item_code
		LEFT JOIN `tabItem Price` AS latest_price
			ON latest_valid.item_code = latest_price.item_code
			AND latest_valid.latest_valid_from = latest_price.valid_from
		INNER JOIN `tabWarehouse` AS warehouse
			ON warehouse.name = ledger.warehouse
		WHERE
			ledger.actual_qty != 0 {1}
		""".format(columns, conditions)
	)

	return data