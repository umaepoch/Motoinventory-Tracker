# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
import time
import math
import ast
import os.path
import sys
print sys.path

from frappe import _, msgprint, throw, utils
from datetime import datetime, timedelta
from frappe.utils import flt, getdate, datetime,comma_and
from collections import defaultdict
from werkzeug.wrappers import Response

reload(sys)
sys.setdefaultencoding('utf-8')


def execute(filters=None):
	columns = get_columns()
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)

	item_details = get_item_details(items, sl_entries)

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
	qty_prev = 0

	item_work = ""
	serial_work = ""
	vehstatus_work = ""
	vtype_work = ""
	vouch_work = ""
	brn_work = ""
	whse_work = ""
	qty_work = 0

	alloc_whse_count = 0
	unalloc_whse_count = 0

	total_count = 0
	item_count = 1
	in_item_count = 0
	out_item_count = 0
	whse_count = 0
	in_whse_count = 0
	out_whse_count = 0
	alloc_unalloc = ""
	opening_qty = 0
	qty_diff = 0
	open_qty = 0
	in_qty = 0
	out_qty = 0

	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

#	if opening_row:
#		frappe.msgprint(_(opening_row))
#		data.append(opening_row)

	for sle in sl_entries:
		item_detail = item_details[sle.item_code]
		data.append([sle.item_code, sle.warehouse, sle.voucher_type, sle.voucher_no, sle.serial_no, sle.vehicle_status, sle.booking_reference_number, sle.actual_qty, sle.qty_after_transaction, sle.posting_date])

	for rows in data:


		if total_count == 0:
#			opening_qty = get_opening_balance(rows[0], filters)
			summ_data.append([rows[1], rows[0], "", "", "", "", "", opening_qty, "", "", ""])
			item_prev = rows[0]
			whse_prev = rows[1]
			vtype_prev = rows[2]
			vouch_prev = rows[3]
			serial_prev = rows[4]
			vehstatus_prev = rows[5]
			brn_prev = rows[6]
			qty_prev = rows[7]

			if rows[6]:
				alloc_whse_count = alloc_whse_count + 1
			else:
				unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
		
			if rows[6] and rows[5] == "Allocated but not Delivered":
				alloc_unalloc = "Allocated"
			else:
				alloc_unalloc = "Unallocated"

			if rows[9] < from_date:
				open_qty += qty_prev

			elif rows[9] >= from_date and rows[9] <= to_date:
				if qty_prev > 0:
					in_qty += qty_prev
					in_item_count = in_item_count + 1
					summ_data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], rows[5], alloc_unalloc, "", qty_prev, "", ""])

				else:
					out_qty += qty_prev
					out_item_count = out_item_count + 1
					summ_data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], rows[5], alloc_unalloc, "", "", qty_prev, ""])

			
			
		else:
			item_work = rows[0]
			whse_work = rows[1]			
			vtype_work = rows[2]
			vouch_work = rows[3]
			serial_work = rows[4]
			vehstatus_work = rows[5]
			brn_work = rows[6]
			qty_work = rows[7]

			if item_prev == item_work:
				if rows[6] and rows[5] == "Allocated but not Delivered":
					alloc_unalloc = "Allocated"
				else:
					alloc_unalloc = "Unallocated"

				item_count = item_count + 1
				if qty_work > 0:
					in_item_count = in_item_count + 1
					summ_data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], rows[5], alloc_unalloc, "", qty_work, "", ""])
				else:
					out_item_count = out_item_count + 1
					summ_data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], rows[5], alloc_unalloc, "", "", qty_work, ""])


			else:
#				if qty_prev > 0:
#					in_item_count = in_item_count + 1
#				else:
#					out_item_count = out_item_count + 1

				summ_data.append(["", item_prev, "", "", "", "", "", "", in_item_count, out_item_count, (opening_qty + in_item_count - out_item_count)])
				opening_qty = get_opening_balance(item_work, filters)
				summ_data.append([whse_prev, item_work, "", "", "", "", "", opening_qty, "", "", ""])

				item_count = 0
				in_item_count = 0
				out_item_count = 0
				item_prev = item_work

				if brn_work and vehstatus_work == "Allocated but not Delivered":
					alloc_unalloc = "Allocated"
				else:
					alloc_unalloc = "Unallocated"

				if qty_work > 0:
					in_item_count = in_item_count + 1
					summ_data.append([whse_work, item_work, vtype_work, vouch_work, serial_work, vehstatus_work, alloc_unalloc, "", qty_work, "", ""])
				else:
					out_item_count = out_item_count + 1
					summ_data.append([whse_work, item_work, vtype_work, vouch_work, serial_work, vehstatus_work, alloc_unalloc, "", "", qty_work, ""])
#					summ_data.append(["", item_pr, "", "", "", "", "", in_item_count, out_item_count, item_count])

 
							
			serial_prev = serial_work	
			vehstatus_prev = vehstatus_work
			brn_prev = brn_work
			vtype_prev = vtype_work
			vouch_prev = vouch_work
			qty_prev = qty_work
			if rows[6]:
				alloc_whse_count = alloc_whse_count + 1
			else:
				unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
			
		total_count = total_count +1

#	if qty_work > 0:
#		in_item_count = in_item_count + 1
#		summ_data.append([whse_work, item_work, vtype_work, vouch_work, serial_work, vehstatus_work, brn_work, qty_work, "", ""])	
#	else:
#		out_item_count = out_item_count + 1
#		summ_data.append([whse_work, item_work, vtype_work, vouch_work, serial_work, vehstatus_work, brn_work, "", qty_work, ""])

	summ_data.append(["", item_work, "", "", "", "", "", "", in_item_count, out_item_count, (opening_qty + in_item_count - out_item_count)])
	summ_data.append(["", "", "", "", "", "", "", "", "", "", ""])
	summ_data.append(["", "", "", "", "", "", "", "", "", "", ""])
	summ_data.append([whse_work, "Allocated", alloc_whse_count, "", "", "", "Unallocated", unalloc_whse_count, "", "", whse_count])
	
	return columns, summ_data

def get_columns():
	columns = [

		_("Warehouse") + ":Link/Warehouse:100", 
		_("Item") + ":Link/Item:130",
		_("Voucher Type") + "::110",
		_("Voucher #") + "::100",
		_("Serial #") + ":Link/Serial No:100",
		_("Vehicle Status") +"::100",
		_("Allocated ?")+"::100",
		_("Opening Qty") +":Int:100",
		_("In Qty")+":Int:100",
		_("Out Qty")+":Int:100",
		_("Bal Qty") + ":Int:50"


	]

	return columns

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	conditions = get_sle_conditions(filters)
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join(['"' + frappe.db.escape(i,percent=False) + '"' for i in items]))

#	return frappe.db.sql("""select sle.posting_date,
#			sle.item_code, sle.warehouse, sle.actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
#			stock_value, voucher_type, voucher_no, sle.serial_no, sn.vehicle_status, sn.booking_reference_number
#		from `tabStock Ledger Entry` sle, `tabSerial No` sn
#		where sle.serial_no = sn.name %s order by sle.item_code asc, sle.actual_qty desc""" % conditions, as_dict=1)

	return frappe.db.sql("""select sle.posting_date,
			sle.item_code, sle.warehouse, sle.actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, sle.serial_no, sn.vehicle_status, sn.booking_reference_number
		from `tabStock Ledger Entry` sle, `tabSerial No` sn where sle.serial_no = sn.name and posting_date <= %s and sle.warehouse = %s order by item_code asc, sle.actual_qty desc""", (filters.get("from_date"), filters.get("to_date"), filters.get("warehouse")), as_dict=1)



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
#	conditions = ""
#	conditions = "sle.posting_date >= CURDATE() - 30"

#	if filters.get("warehouse"):
#		conditions += " and sle.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)

#	return conditions

	conditions = []
#	if filters.get("from_date"):
#		frappe.msgprint(_(filters.get("from_date")))
#		conditions.append("posting_date between %(from_date)s and %(to_date)s")
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)

	return "and {}".format(" and ".join(conditions)) if conditions else ""



def get_opening_balance(item, filters):
	
	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": item,
		"warehouse": filters.get("warehouse"),
		"posting_date": filters.get("from_date"),
		"posting_time": "00:00:00"
	})

	return last_entry.get('qty_after_transaction')
#	row = [""]*len(columns)
#	row[1] = _("'Opening'")
#	for i, v in ((9, 'qty_after_transaction'), (11, 'valuation_rate'), (12, 'stock_value')):
#			row[i] = last_entry.get(v, 0)

#	return row

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
