# Copyright (c) 2023, connect and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns(filters)
	stock = get_total_stock(filters)

	return columns, stock


def get_columns(filters):

	columns = [
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options" : "Company",
			"width": "120"
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options" : "Warehouse",
			"width": "120"
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options" : "Item",
			"width": "90"
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": "120"
		},
		{
			"fieldname": "actual_qty",
			"label": _("Current Qty"),
			"fieldtype": "Float",
			"width": "100"
		},
		{
			"fieldname": "valuation_rate",
			"label": _("Valuation Rate"),
			"fieldtype": "Currency",
			"width": "90"
		},
		{
			"fieldname": "last_purchase_rate",
			"label": _("Last Purchase Rate"),
			"fieldtype": "Float",
			"width": "90"
		},
		{
			"fieldname": "max_discount",
			"label": _("Max Discount (%)"),
			"fieldtype": "Float",
			"width": "90"
		},
		{
			"fieldname": "price_list_rate",
			"label": _("Price List Rate"),
			"fieldtype": "Currency",
			"width": "90"
		},
		{
			"fieldname": "total",
			"label": _("Total"),
			"fieldtype": "Currency",
			"width": "90"
		},
	] 
	if filters.get("price_list"):
		currency = frappe.db.get_value(
					"Price List", f'{filters.get("price_list")}', "currency"
				)
		if currency != 'EGP':
			# columns.append({"label": _("Factor Exchange Rate"), "fieldname": "factor", "width": 90, "fieldtype": "Float"})
			columns.append({"label": _("Unit Price"), "fieldname": "unit_price", "width": 90, "fieldtype": "Float"})
			columns.append({"label": _("Total After Factor"), "fieldname": "total_after_rate", "width": 90, "fieldtype": "Float"})


	return columns


def get_total_stock(filters):
	conditions = ""
	columns = ""

	if filters.get("item") :
		conditions += f'AND item.item_code = "{filters.get("item")}" '

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

		conditions += " GROUP BY warehouse.company,item.item_code"
		columns += " warehouse.company, '' as warehouse"

	data = frappe.db.sql(
		"""
		SELECT
			{0},
			item.item_code,
			item.valuation_rate ,
			item.description,
			sum(ledger.actual_qty) as actual_qty,
			item.last_purchase_rate,
			item.max_discount,
			COALESCE(latest_price.price_list_rate, 0) as price_list_rate,
			(sum(ledger.actual_qty)   * COALESCE(latest_price.price_list_rate, 0)) as total,
			latest_price.price_list ,
			latest_price.currency ,
			(
				SELECT c.exchange_rate
				FROM `tabCurrency Exchange` c 
				WHERE c.from_currency = latest_price.currency 
				ORDER BY c.creation DESC 
				LIMIT 1
			) AS factor ,
			( (
				SELECT c.exchange_rate
				FROM `tabCurrency Exchange` c 
				WHERE c.from_currency = latest_price.currency 
				ORDER BY c.creation DESC 
				LIMIT 1
			)  * COALESCE(latest_price.price_list_rate, 0) ) as unit_price ,
			(
			(
				SELECT c.exchange_rate
				FROM `tabCurrency Exchange` c 
				WHERE c.from_currency = latest_price.currency 
				ORDER BY c.creation DESC 
				LIMIT 1
			)  * COALESCE(latest_price.price_list_rate, 0) * sum(ledger.actual_qty)
			) as total_after_rate
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
			

		""".format(columns, conditions), as_dict = 1
	)
	return data
