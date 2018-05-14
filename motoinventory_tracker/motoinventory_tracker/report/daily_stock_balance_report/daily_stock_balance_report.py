# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint

def execute(filters=None):
	columns = get_columns()
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries)
	opening_row = get_opening_balance(filters, columns)

	data = []
	summ_data = []
	data = []
	item_prev = ""
	serial_prev = ""
	vehstatus_prev = ""
	vtype_prev = ""
	vouch_prev = ""
	brn_prev = ""
	whse_prev = ""

	item_work = ""
	serial_work = ""
	vehstatus_work = ""
	vtype_work = ""
	vouch_work = ""
	brn_work = ""
	whse_work = ""

	alloc_whse_count = 0
	unalloc_whse_count = 0

	tot_whse_count = 0
	total_count = 0
	item_count = 1
	whse_count = 0

#	if opening_row:
#		data.append(opening_row)

	for sle in sl_entries:
		item_detail = item_details[sle.item_code]

		data.append([sle.item_code, sle.warehouse, sle.voucher_type, sle.voucher_no, sle.serial_no, sle.vehicle_status, sle.booking_reference_number, sle.actual_qty, sle.qty_after_transaction])

	for rows in data:
#		print rows
		if total_count == 0:
			item_prev = rows[0]
			whse_prev = rows[1]
			vtype_prev = rows[2]
			vouch_prev = rows[3]
			serial_prev = rows[4]
			vehstatus_prev = rows[5]
			brn_prev = rows[6]

			summ_data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], rows[5], rows[6], ""])
			if rows[6]:
				alloc_whse_count = alloc_whse_count + 1
			else:
				unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
			
		else:
			item_work = rows[0]
			whse_work = rows[1]			
			vtype_work = rows[2]
			vouch_work = rows[3]
			serial_work = rows[4]
			vehstatus_work = rows[5]
			brn_work = rows[6]

			if item_prev == item_work:
				summ_data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], rows[5], rows[6], ""])
				item_count = item_count + 1

			else:
				if total_count == 1:
					summ_data.append(["", item_prev, "", "", "", "", "", item_count])
				else:
					summ_data.append([whse_prev, item_prev, vtype_prev, vouch_prev, serial_prev, vehstatus_prev, brn_prev, ""])
					summ_data.append(["", item_prev, "", "", "", "", "", item_count])

 
				item_count = 1
				item_prev = item_work
				serial_prev = serial_work
				whse_prev = whse_work
				vehstatus_prev = vehstatus_work
				brn_prev = brn_work
				vtype_prev = vtype_work
				vouch_prev = vouch_work
			if rows[6]:
				alloc_whse_count = alloc_whse_count + 1
			else:
				unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
			
		total_count = total_count +1

		summ_data.append([whse_work, item_work, vtype_work, vouch_work, serial_work, vehstatus_work, brn_work, ""])	
		summ_data.append(["", item_work, "", "", "", "", "", item_count])

		summ_data.append([whse_work, "Allocated", alloc_whse_count, "Unallocated", unalloc_whse_count, whse_count])

	return columns, data

def get_columns():
	columns = [

		_("Item") + ":Link/Item:130",
		_("Warehouse") + ":Link/Warehouse:100", 
		_("Voucher Type") + "::110",
		_("Voucher #") + "::100",
		_("Serial #") + ":Link/Serial No:100",
		_("Vehicle Status") +"::100",
		_("Booking Reference")+"::100",
		_("Qty") + ":Int:50", 
		_("Balance Qty") + ":Int:100"


	]

	return columns

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join(['"' + frappe.db.escape(i,percent=False) + '"' for i in items]))

	return frappe.db.sql("""select concat_ws(" ", posting_date, posting_time) as date,
			sle.item_code, sle.warehouse, sle.actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, sle.serial_no, sn.vehicle_status, sn.booking_reference_number
		from `tabStock Ledger Entry` sle, `tabSerial No` sn
		where sle.serial_no = sn.name and
			posting_date between %(from_date)s and %(to_date)s
			{sle_conditions}
			{item_conditions_sql}
			order by sle.item_code asc, posting_date asc, posting_time asc"""\
		.format(
			sle_conditions=get_sle_conditions(filters),
			item_conditions_sql = item_conditions_sql
		), filters, as_dict=1)

def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sl_entries):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sl_entries]))

	if not items:
		return item_details

	for item in frappe.db.sql("""
		select name, item_name, description, item_group, brand, stock_uom
		from `tabItem`
		where name in ({0})
		""".format(', '.join(['"' + frappe.db.escape(i,percent=False) + '"' for i in items])), as_dict=1):
			item_details.setdefault(item.name, item)

	return item_details

def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("project=%(project)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_opening_balance(filters, columns):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": filters.item_code,
		"warehouse_condition": get_warehouse_condition(filters.warehouse),
		"posting_date": filters.from_date,
		"posting_time": "00:00:00"
	})
	row = [""]*len(columns)
	row[1] = _("'Opening'")
	for i, v in ((9, 'qty_after_transaction'), (11, 'valuation_rate'), (12, 'stock_value')):
			row[i] = last_entry.get(v, 0)

	return row

def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''

def get_item_group_condition(item_group):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		return "item.item_group in (select ig.name from `tabItem Group` ig \
			where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"%(item_group_details.lft,
			item_group_details.rgt)

	return ''
