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

	report_data = []
	data = []
	item_prev = ""
	item_work = ""
	serial_work = ""
	whse_work = ""
	serial_prev = ""
	whse_prev = ""
	vehstatus_prev = ""
	brn_prev = ""
	vehstatus_work = ""
	brn_work = ""
	whse_count = 0
	alloc_whse_count = 0
	unalloc_whse_count = 0

	tot_whse_count = 0
	tot_alloc_whse_count = 0
	tot_unalloc_whse_count = 0

	total_count = 0
	item_count = 1
	for (warehouse, item, serial_number) in sorted(iwb_map):
		qty_dict = iwb_map[(warehouse, item, serial_number)]
		report_data.append([warehouse, item, serial_number, qty_dict.vehicle_status, qty_dict.brn])
	
	for rows in report_data:
		if total_count == 0:
			whse_prev = rows[0]
			item_prev = rows[1]
			brn_prev = rows[4]
#			data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], ""])
			if rows[4]:
				alloc_whse_count = alloc_whse_count + 1
			else:
				unalloc_whse_count = unalloc_whse_count + 1

			whse_count = whse_count + 1
			
		else:
			whse_work = rows[0]			
			item_work = rows[1]
			serial_work = rows[2]
			vehstatus_work = rows[3]
			brn_work = rows[4]

			if whse_prev == whse_work:
	
				tot_whse_count = whse_count + 1

				if item_prev == item_work:
#					data.append([whse_prev, item_prev, rows[2], rows[3], rows[4], ""])
					item_count = item_count + 1

				else:

 
					item_count = 1
					item_prev = item_work
					serial_prev = serial_work
					whse_prev = whse_work
					vehstatus_prev = vehstatus_work
					brn_prev = brn_work
				if rows[4]:
					alloc_whse_count = alloc_whse_count + 1
				else:
					unalloc_whse_count = unalloc_whse_count + 1

				whse_count = whse_count + 1
			else:
#				data.append([whse_prev, item_prev, serial_prev, vehstatus_prev, brn_prev, ""])
#				data.append(["", item_prev, "", "", "", item_count])
				data.append([whse_prev, unalloc_whse_count, alloc_whse_count, whse_count])
#				data.append([whse_work, item_work, serial_work, ""])
				tot_alloc_whse_count = tot_alloc_whse_count + alloc_whse_count
				tot_unalloc_whse_count = tot_unalloc_whse_count + unalloc_whse_count
				item_count = 1
				item_prev = item_work
				serial_prev = serial_work
				whse_prev = whse_work
				vehstatus_prev = vehstatus_work
				brn_prev = brn_work
				whse_count = 1
				alloc_whse_count = 0
				unalloc_whse_count = 1
				
		total_count = total_count +1

	tot_alloc_whse_count = tot_alloc_whse_count + alloc_whse_count
	tot_unalloc_whse_count = tot_unalloc_whse_count + unalloc_whse_count

#	data.append([whse_work, item_work, serial_work, ""])
	data.append([whse_work, unalloc_whse_count, alloc_whse_count, whse_count])
	data.append(["Total", tot_unalloc_whse_count, tot_alloc_whse_count, total_count])

	return columns, data


def get_columns():
	"""return columns"""

	columns = [
		_("Warehouse")+"::150",
		_("Free Stock")+":Int:120",
		_("Allocated")+":Int:120",
		_("Total")+":Int:100"
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
		select sn.item_code as item_code, sn.name as serial_number, sn.warehouse as warehouse, sn.vehicle_status as vehicle_status, sn.booking_reference_number as brn from `tabSerial No` sn 
where sn.warehouse is not NULL %s order by sn.item_code""" % conditions, as_dict=1)

	
def get_item_warehouse_map(filters):
	iwb_map = {}

	sle = get_stock_ledger_entries(filters)

	for d in sle:
		warehouse, company = d.warehouse.split('-')

		key = (warehouse, d.item_code, d.serial_number)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"total": 0.0
			})

		qty_dict = iwb_map[(warehouse, d.item_code, d.serial_number)]
		qty_dict.item_code = d.item_code
		qty_dict.serial_no = d.serial_number
		qty_dict.vehicle_status = d.vehicle_status
		qty_dict.brn = d.brn
		
		
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




