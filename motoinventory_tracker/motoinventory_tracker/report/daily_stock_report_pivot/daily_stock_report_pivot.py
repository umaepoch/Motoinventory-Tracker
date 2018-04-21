# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, utils
from frappe.utils import flt, cint, getdate, datetime
from datetime import datetime, timedelta

def execute(filters=None):
	if not filters: filters = {}

	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)
	columns, warehouse_list = get_columns(iwb_map)
	frappe.msgprint(_(warehouse_list))
#	whse_stock_map = get_whse_stock_map(warehouse_list)

	report_data = []
	data = []
	item_prev = ""
	item_work = ""
	serial_work = ""
	whse_work = ""
	serial_prev = ""
	whse_prev = ""

	total_count = 0
	item_count = 0
	for (item, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(item, warehouse)]
		report_data.append([item, warehouse
		])
	
	for rows in report_data:
		if total_count == 0:
			item_prev = rows[0]
			item_count = item_count + 1
			
		else:
			item_work = rows[0]
			whse_work = rows[1]

			if item_prev == item_work:
				item_count = item_count + 1

			else:
				if item_count == 0:
					data.append([item_prev, whse_prev, item_count+1])
				else:
					data.append([item_prev, whse_prev, item_count])

				item_count = 0
				item_prev = item_work
				serial_prev = serial_work
				whse_prev = whse_work

		total_count = total_count + 1
	if item_count == 0:	
		data.append([item_work, whse_work, item_count+1])
	else:
		data.append([item_work, whse_work, item_count+1])

	pivot_data = []

	for p in data:
		row = [p[0]]

		for whse in warehouse_list:
			row[whse] = [p[2]]
		frappe.msgprint(_(row))


		pivot_data.append(row)

	return columns, pivot_data


def get_columns(iwb_map):
	"""return columns"""

	columns = [
		_("Item")+":Link/Item:120",
		_("Warehouse")+"::150",
		_("Total")+"::100"
	]
	
	whse_list = frappe.db.sql("""select distinct sn.warehouse as warehouse from `tabSerial No` sn 
where sn.warehouse is not NULL""", as_dict=1)
	whse_components = []
	for whse in whse_list:
#		whse_components[_(whse.warehouse)].append(whse.warehouse)
		whse_components.append(whse.warehouse)
		frappe.msgprint(_(whse_components))
	frappe.msgprint(_(columns))
	for e in whse_components:
		frappe.msgprint(_(e))
	columns = columns + [(e + "::120") for e in whse_components] 

	return columns, whse_components



def get_conditions(filters):
	conditions = ""

	if filters.get("warehouse"):
		conditions = " and sn.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)

	return conditions

def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	
	join_table_query = ""
	
	return frappe.db.sql("""
		select sn.item_code as item_code, sn.warehouse as warehouse from `tabSerial No` sn 
where sn.warehouse is not NULL %s order by sn.item_code""" % conditions, as_dict=1)

	
def get_item_warehouse_map(filters):
	iwb_map = {}

	sle = get_stock_ledger_entries(filters)

	for d in sle:
		key = (d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"total": 0.0
			})

		qty_dict = iwb_map[(d.item_code, d.warehouse)]
		qty_dict.item_code = d.item_code
		qty_dict.warehouse = d.warehouse
		
		
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

def get_whse_stock_map(salary_struc):

	ss_earnings = frappe.db.sql("""select sd.parent, sd.salary_component, sd.amount
		from `tabSalary Detail` sd, `tabSalary Structure` ss where sd.parent = ss.name""", as_dict=1)
	
	ss_earning_map = {}
	for d in ss_earnings:
		ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
		ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

	return ss_earning_map



