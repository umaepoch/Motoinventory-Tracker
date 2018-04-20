# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, utils
from frappe.utils import flt, cint, getdate, datetime
from datetime import datetime, timedelta

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)

	data = []
	for (item, serial_number, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(item, serial_number, warehouse)]
		if qty_dict.actual_qty > 0:
			report_data = [item, serial_number, warehouse, qty_dict.actual_qty
			]


			data.append(report_data)


	return columns, data

def get_columns():
	"""return columns"""

	columns = [
		_("Item")+":Link/Item:120",
		_("Serial No")+":Link/Serial No:120",
		_("Warehouse")+"::150",
		_("Qty")+":Float:100"
	]

	return columns

def get_conditions(filters):
	conditions = ""

	if filters.get("warehouse"):
		conditions = " and sle.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)

	return conditions

def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	
	join_table_query = ""
	
	return frappe.db.sql("""
		select
			sle.item_code, sle.serial_no, sle.warehouse, sle.posting_date, sle.actual_qty
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index) %s
		where sle.docstatus < 2 and sle.warehouse is not NULL %s 
		order by sle.posting_date, sle.posting_time, sle.name""" %
		(join_table_query, conditions), as_dict=1)

	

def get_item_warehouse_map(filters):
	iwb_map = {}

	sle = get_stock_ledger_entries(filters)

	for d in sle:
		key = (d.item_code, d.serial_no, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"actual_qty": 0.0
			})

		qty_dict = iwb_map[(d.item_code, d.serial_no, d.warehouse)]
		qty_dict.item_code = d.item_code
		qty_dict.serial_no = d.serial_no
		qty_dict.warehouse = d.warehouse
		qty_dict.actual_qty = d.actual_qty
		
		
	iwb_map = filter_items_with_no_transactions(iwb_map)

	return iwb_map
	
def filter_items_with_no_transactions(iwb_map):
	for (item_code, serial_no, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(item_code, serial_no, warehouse)]
		
		no_transactions = True
		float_precision = cint(frappe.db.get_default("float_precision")) or 3
		for key, val in qty_dict.items():
			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False
		
		if no_transactions:
			iwb_map.pop((company, item, warehouse))

	return iwb_map

def get_item_details(filters):
	condition = ''
	value = ()
	if filters.get("item_code"):
		condition = "where item_code=%s"
		value = (filters.get("item_code"),)

	items = frappe.db.sql("""
		select name, item_name, stock_uom, item_group, brand, description
		from tabItem
		{condition}
	""".format(condition=condition), value, as_dict=1)

	item_details = dict((d.name , d) for d in items)


	return item_details




