# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, utils, throw
from frappe.utils import flt, cint, getdate, datetime
from datetime import datetime, timedelta

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)
#	opening_row = get_opening_balance(filters, columns)

	report_data = []
	data = []
	item_prev = ""
	item_work = ""
	serial_work = ""
	serial_prev = ""
	vehstatus_prev = ""
	brn_prev = ""
	vehstatus_work = ""
	brn_work = ""
	whse_count = 0
	alloc_whse_count = 0
	unalloc_whse_count = 0
	in_qty = 0
	out_qty = 0
	curr_date = utils.today()

	total_count = 0
	item_count = 1
	for (item, vehicle_status, serial_number) in sorted(iwb_map):
		qty_dict = iwb_map[(item, vehicle_status, serial_number)]
		report_data.append([item, serial_number, vehicle_status, qty_dict.brn, qty_dict.crt_date, qty_dict.ddn, qty_dict.del_date, qty_dict.customer])

	for rows in report_data:
		if total_count == 0:
			item_prev = rows[0]
			brn_prev = rows[3]
			warehouse = filters.get("warehouse")
#			open_row = open_stock(warehouse)
			if (curr_date == rows[4]):
				data.append([warehouse, item_prev, rows[1], rows[2], rows[3], ""])
			if rows[3]:
				alloc_whse_count = alloc_whse_count + 1
			else:
				unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
			
		else:
			item_work = rows[0]
			serial_work = rows[1]
			vehstatus_work = rows[2]
			brn_work = rows[3]
			
			if item_prev == item_work:
				data.append([warehouse, item_prev, rows[1], rows[2], rows[3], ""])
				item_count = item_count + 1

			else:
				if total_count == 1:
					data.append(["", item_prev, "", "", "", item_count])
				else:
					data.append([warehouse, item_prev, serial_prev, vehstatus_prev, brn_prev, ""])
					data.append(["", item_prev, "", "", "", item_count])

 
				item_count = 1
				item_prev = item_work
				serial_prev = serial_work
				vehstatus_prev = vehstatus_work
				brn_prev = brn_work
			
				if rows[4]:
					alloc_whse_count = alloc_whse_count + 1
				else:
					unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
			total_count = total_count + 1
				
	data.append([warehouse, "Allocated", alloc_whse_count, "Unallocated", unalloc_whse_count, whse_count])

	return columns, data


def get_columns():
	"""return columns"""

	columns = [
		_("Warehouse")+"::150",
		_("Item")+"::120",
		_("Serial No")+"::120",
		_("Vehicle Status")+"::120",
		_("Booking Reference No")+"::120",
#		_("Customer")+"::120",
#		_("In Qty")+"::120",
#		_("Out Qty")+"::120",
#		_("Bal Qty")+"::120",
		_("Total")+"::100"
	]

	return columns

def get_conditions(filters):
	conditions = ""

	if filters.get("warehouse"):
		conditions = " and sn.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)

	return conditions

def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	
	join_table_query = ""
	
	return frappe.db.sql("""
		select sn.item_code as item_code, sn.name as serial_number, sn.warehouse as warehouse, sn.vehicle_status as vehicle_status, sn.booking_reference_number as brn, sn.customer, sn.purchase_date, sn.delivery_document_no, sn.delivery_date from `tabSerial No` sn 
where sn.warehouse is not NULL %s order by sn.item_code""" % conditions, as_dict=1)

	
def get_item_warehouse_map(filters):
	iwb_map = {}

	sle = get_stock_ledger_entries(filters)

	for d in sle:
		key = (d.item_code, d.vehicles_status, d.serial_number)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"total": 0.0
			})

		qty_dict = iwb_map[(d.item_code, d.vehicles_status, d.serial_number)]
		qty_dict.item_code = d.item_code
		qty_dict.serial_no = d.serial_number
		qty_dict.warehouse = d.warehouse
		qty_dict.vehicle_status = d.vehicle_status
		qty_dict.brn = d.brn
		qty_dict.customer = d.customer
		qty_dict.ddn = d.delivery_document_no
		qty_dict.del_date = d.delivery_date
		qty_dict.crt_date = d.purchase_date
		
		
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




def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''

