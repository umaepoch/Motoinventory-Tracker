from __future__ import unicode_literals
import frappe
import json
import time
import math
import ast
import os.path
import sys
import datetime
import time
from datetime import datetime
print sys.path
from frappe import _, msgprint, throw, utils
from frappe.utils import flt, getdate,comma_and
from collections import defaultdict
from werkzeug.wrappers import Response
reload(sys)
sys.setdefaultencoding('utf-8')

def execute(filters=None):
	columns = get_columns()
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries)
	global summ_data
	global warehouse
	data = []
	summ_data = []
	data = []
	item_prev = ""
	opening_qty = 0
	warehouse = filters.get("warehouse")
	for sle in sl_entries:
		#item_detail = item_details[sle.item_code]
		item_code = filters.get("item_code")
		if filters.get("warehouse") and filters.get("item_code"):
			if str(sle.item_code) == str(item_code):
				data.append([sle.item_code, sle.warehouse, sle.voucher_type, sle.voucher_no, sle.serial_no, sle.vehicle_status, 				sle.booking_reference_number, sle.actual_qty, sle.qty_after_transaction])
				item = filters.get("item_code")
		else:
			data.append([sle.item_code, sle.warehouse, sle.voucher_type, sle.voucher_no, sle.serial_no, sle.vehicle_status, 			sle.booking_reference_number, sle.actual_qty, sle.qty_after_transaction])
	outward_list = []
	inward_list = []
	items_in_stock_list = []
	in_serialid_list = []
	out_serialid_list = []
	if filters.get("warehouse") and filters.get("item_code"):
		opening_qty = get_opening_balance(filters)
	else:
		opening_qty = get_opening_stock(filters)
	print "opening_qty-------", opening_qty
	
	for rows in data:
		print "serialID-------", rows[4]
		print "item-------", rows[0]
		print "actual_qty-------", rows[7]
		actual_qty = rows[7]
		serial_no = rows[4]
		item_prev = rows[0]
		whse_prev = rows[1]
		voucher_type = rows[2]
		voucher_no = rows[3]
		inward_outward_status = ""
		booking_reference_number = ""
		customer_details = ""

		if actual_qty > 0:
			items_data = {}
			whse_data = ""
			if voucher_type == "Stock Entry":
				whse = get_destination_warehouse(voucher_no)
				purpose = whse[0]['purpose']
				if purpose == "Material Transfer":
					dest_whse = whse[0]['s_warehouse']
					if dest_whse is not None:
						whse_data = "Transfered From "
						whse_data = whse_data + str(dest_whse)
				elif purpose == "Material Receipt":
					dest_whse = whse[0]['s_warehouse']
					if dest_whse is not None:
						whse_data = "Received From "
						whse_data = whse_data + str(dest_whse)
					else:
						whse_data = "Received From RE/Dealer"
			items_data = {"whse":whse_prev,"item":item_prev,"serial_id":rows[4],"dest_whse":whse_data}
			inward_list.append(items_data)
			in_serialid_list.append(serial_no)
			
		else:
			print "sid------", rows[4]
			print "voucher_type------", rows[2]
			items_data = {}
			whse_data = ""
			if voucher_type == "Stock Entry":
				whse = get_destination_warehouse(voucher_no)
				purpose = whse[0]['purpose']
				print "purpose------", purpose
				if purpose == "Material Transfer" or purpose == "Material Receipt":
					dest_whse = whse[0]['t_warehouse']
					if dest_whse is not None:
						whse_data = "Transfered To "
						whse_data = whse_data + str(dest_whse)
			else:
				customer_details = get_customer(serial_no)
				customer_name = customer_details[0]['customer_name']
				if customer_name is not None and customer_name is not "":
					whse_data = "Delivered To "
					whse_data = whse_data + str(customer_name)
			items_data = {"whse":whse_prev,"item":item_prev,"serial_id":rows[4],"dest_whse":whse_data}
			outward_list.append(items_data)
			out_serialid_list.append(serial_no)
	allocation_count = 0
	unallocation_count = 0
	stock_ids_list = []
	stock_details = get_items_in_stock(filters)
	print "stock_ids_list-----", stock_details
	for data in stock_details:
		if data['serial_no'] is not None:
			customer_details = get_customer(serial_no)
			booking_reference_number = customer_details[0]['booking_reference_number']
			item_code = customer_details[0]['item_code']
			if booking_reference_number is not None and booking_reference_number is not "":
				inward_outward_status = customer_details[0]['vehicle_status']
				allocation_count = allocation_count + 1
			else:
				inward_outward_status = "Free Stock"
				unallocation_count = unallocation_count + 1
			items_data = {"whse":warehouse,"item":item_code,"serial_id":data['serial_no'], 					    						"inward_outward_status": inward_outward_status}
			items_in_stock_list.append(items_data)
	summ_data.append(["Opening Stock", "", "Total:",opening_qty])
	summ_data.append(["Vehicles Inward", "","", ""])
	for data in inward_list:
		summ_data.append([data['whse'], data['item'], data['serial_id'], data['dest_whse']])
	summ_data.append(["", "","", ""])
	summ_data.append(["", "","", ""])

	summ_data.append(["Vehicles Outward", "","", ""])
	for data in outward_list:
		summ_data.append([data['whse'], data['item'], data['serial_id'], data['dest_whse']])
	summ_data.append(["", "","", ""])
	summ_data.append(["", "","", ""])

	summ_data.append(["Vehicles In Stock", "","", ""])
	for data in items_in_stock_list:
		summ_data.append([data['whse'], data['item'], data['serial_id'], data['inward_outward_status']])
	summ_data.append(["", "","", ""])
	summ_data.append(["", "","", ""])

	summ_data.append([warehouse, "Allocated", allocation_count, "Unallocated", unallocation_count, "Total:", (allocation_count + 				unallocation_count)])
	if allocation_count:
		allocation_count = 0
	if unallocation_count:
		unallocation_count = 0
	return columns, summ_data


def get_destination_warehouse(voucher_no):
	whse = frappe.db.sql(""" select sed.item_code,sed.t_warehouse,se.purpose,sed.s_warehouse from `tabStock Entry Detail` sed, 
				`tabStock Entry` se where sed.parent = %s and sed.parent = se.name""", voucher_no, as_dict=1)
	return whse

def get_customer(serial_no):
	details = frappe.db.sql(""" select customer_name,booking_reference_number,vehicle_status,item_code from `tabSerial No` where serial_no 			   = %s""", serial_no, as_dict=1)
	return details

def get_items_in_stock(filters):
	if filters.get("warehouse") and filters.get("item_code"):
		item_code = filters.get("item_code")
		stock_list = frappe.db.sql("""select serial_no from `tabStock Entry Detail` where t_warehouse ='"""+warehouse+"""' and 				     serial_no not in (select serial_no from `tabStock Entry Detail` where s_warehouse ='"""+warehouse+"""') and
			     serial_no in(select serial_no from `tabSerial No` where delivery_document_no is null) and item_code=%s""", 			     item_code, as_dict=1)
	else:
		stock_list = frappe.db.sql("""select serial_no from `tabStock Entry Detail` where t_warehouse ='"""+warehouse+"""' and 				     serial_no not in (select serial_no from `tabStock Entry Detail` where s_warehouse ='"""+warehouse+"""') and
			     serial_no in(select serial_no from `tabSerial No` where delivery_document_no is null)""", as_dict=1)
		print "---------------stock_list:", stock_list
	return stock_list
 
def get_columns():
	columns = [

		_("Warehouse") +":100", 
		_("Item") + ":130",
		_("Serial No") + ":100",
		_("Inward/Outward Details")+":100",
		_("UnAllocation Count")+":100",
		_("Total")+":100",
		_("")+":100"
	]

	return columns

def get_opening_balance(filters):
	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": filters.get("item_code"),
		"warehouse": filters.get("warehouse"),
		"posting_date": filters.get("from_date"),
		"posting_time": "00:00:00"
	})
	print "-------last_entry----------", last_entry.get('qty_after_transaction')
	return last_entry.get('qty_after_transaction')

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

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	conditions = get_sle_conditions(filters)
	from_date = str(filters.get("from_date"))
	to_date = str(filters.get("to_date"))
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join(['"' + frappe.db.escape(i,percent=False) + '"' for i in items]))
	return frappe.db.sql("""select sle.posting_date,
			sle.item_code, sle.warehouse, sle.actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, sle.serial_no, sn.vehicle_status, sn.booking_reference_number
		from `tabStock Ledger Entry` sle, `tabSerial No` sn where sle.serial_no = sn.name and posting_date >= %s and posting_date <= %s and sle.warehouse = %s order by item_code asc, sle.actual_qty desc""", (from_date, to_date, filters.get("warehouse")), as_dict=1)

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

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''
def get_opening_stock(filters):
	opening_stock = 0
	warehouse = filters.get("warehouse")
	from_date = filters.get("from_date")
	opening_qty = frappe.db.sql("""select sum(qty_after_transaction) as qty_after_transaction from `tabStock Ledger Entry` where warehouse=%s and posting_date < %s """, (warehouse, from_date), as_dict=1)
	if opening_qty[0]['qty_after_transaction'] is not None:
		opening_stock = opening_qty[0]['qty_after_transaction']
	return opening_stock

