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
	qty_diff = 0
	bal_qty = 0
	warehouse = filters.get("warehouse")
	from_date = getdate(datetime.datetime.now())
	for sle in sl_entries:
		data.append([sle.item_code, sle.warehouse, sle.voucher_type, sle.voucher_no, sle.serial_no, sle.vehicle_status, 			sle.booking_reference_number, sle.actual_qty, sle.qty_after_transaction])

	details = get_opening_balance(filters, items)
	serial_id_count = 0
	for opening_data in details:
		if opening_data.voucher_type == "Stock Reconciliation":
			qty_diff = flt(opening_data.qty_after_transaction) - opening_data.bal_qty
		else:
			qty_diff = flt(opening_data.actual_qty)
		if opening_data.posting_date < from_date:
			opening_qty += qty_diff
		bal_qty += qty_diff

	print "serial_id_count-------", serial_id_count
	print "opening_qty-------", opening_qty
	print "bal_qty-------", bal_qty
	outward_list = []
	inward_list = []
	items_in_stock_list = []
	in_serialid_list = []
	out_serialid_list = []
	total_vehicles_inward = 0
	total_vehicles_outward = 0
	for rows in data:
		actual_qty = rows[7]
		serial_no = rows[4]
		item_prev = rows[0]
		whse_prev = rows[1]
		voucher_type = rows[2]
		voucher_no = rows[3]
		inward_outward_status = ""
		booking_reference_number = ""
		customer_details = ""
		old_date = ""
		if actual_qty > 0:
			items_data = {}
			whse_data = ""
			item_code = ""
			serial_id = ""
			vehicle_status = "inward"
			if voucher_type == "Stock Entry":
				whse = get_destination_warehouse(voucher_no)
				for details in whse:
					purpose = details['purpose']
					item_code = details['item_code']
					serial_id = details['serial_no']
					old_date = str(details['modified'])
					print "item_code------------", item_code
					if purpose == "Material Transfer":
						dest_whse = details['s_warehouse']
						if dest_whse is not None:
							s_warehouse = ""
							whse_data = "Transferred From "
							if dest_whse == "Truck  - HSR":
								s_warehouse = get_serial_no_details(serial_id,old_date,vehicle_status)
								if s_warehouse:
									whse_data = whse_data + str(s_warehouse)
							else:
								whse_data = whse_data + str(dest_whse)
					elif purpose == "Material Receipt":
						dest_whse = details['s_warehouse']
						if dest_whse is not None:
							whse_data = "Received From "
							whse_data = whse_data + str(dest_whse)
						else:
							whse_data = "Received From RE/Dealer"
					items_data = {"whse":whse_prev,"item":item_code,"serial_id":serial_id,"dest_whse":whse_data}
					inward_list.append(items_data)
			else:
				print "Missing------------", voucher_type, voucher_no
			total_vehicles_inward = total_vehicles_inward + 1
		else:
			print "sid------", rows[4]
			print "voucher_type------", rows[2]
			items_data = {}
			whse_data = ""
			customer_name = ""
			item_code = ""
			serial_id = ""
			vehicle_status = "outward"
			if voucher_type == "Stock Entry":
				whse = get_destination_warehouse(voucher_no)
				for details in whse:
					purpose = details['purpose']
					serial_id = details['serial_no']
					old_date = str(details['modified'])
					print "purpose------", purpose
					if purpose == "Material Transfer" or purpose == "Material Receipt":
						dest_whse = details['t_warehouse']
						if dest_whse is not None:
							t_warehouse = ""
							whse_data = "Transferred To "
							if dest_whse == "Truck  - HSR":
								t_warehouse = get_serial_no_details(serial_id,old_date,vehicle_status)
								if t_warehouse:
									whse_data = whse_data + str(t_warehouse)
								else:
									whse_data = "Transferred To Truck"
							else:
								whse_data = whse_data + str(dest_whse)
					items_data = {"whse":whse_prev,"item":details['item_code'],
							"serial_id":details['serial_no'],"dest_whse":whse_data}
					outward_list.append(items_data)
			elif voucher_type == "Delivery Note":
				print "Delivery Note------", voucher_no
				delivery_details = get_delivery_details(voucher_no)
				print "delivery_details------", delivery_details
				for data in delivery_details:
					customer_name = data['customer']
					item_code = data['item_code']
					serial_id = data['serial_no']
					if customer_name is not None and customer_name is not "":
						whse_data = "Delivered To "
						whse_data = whse_data + str(customer_name)
					items_data = {"whse":whse_prev,"item":item_code,"serial_id":serial_id,"dest_whse":whse_data}
					outward_list.append(items_data)
			elif voucher_type == "Sales Invoice":
				print "voucher_no------", voucher_no
				sales_invoice_details = get_sales_invoice_details(voucher_no)
				print "sales_invoice_details------", sales_invoice_details
				for data in sales_invoice_details:
					customer_name = data['customer']
					item_code = data['item_code']
					serial_id = data['serial_no']
					if customer_name is not None and customer_name is not "":
						whse_data = "Delivered To "
						whse_data = whse_data + str(customer_name)
					items_data = {"whse":whse_prev,"item":item_code,"serial_id":serial_id,"dest_whse":whse_data}
					outward_list.append(items_data)
			else:
				print "Missing------------", voucher_type, voucher_no
			total_vehicles_outward = total_vehicles_outward + 1
	allocation_count = 0
	unallocation_count = 0
	stock_ids_list = []
	stock_details = get_items_in_stock(filters)
	print "stock_ids_list-----", stock_details
	for data in stock_details:
		inward_outward_status = ""
		if data['serial_no'] is not None:
			serial_no = str(data['serial_no'])
			booking_reference_number = data['booking_reference_number']
			item_code = data['item_code']
			'''
			customer_details = get_customer(serial_no)
			booking_reference_number = customer_details[0]['booking_reference_number']
			item_code = customer_details[0]['item_code']
			delivery_date = customer_details[0]['delivery_date']
			warehouse = str(customer_details[0]['warehouse'])
			'''
			if booking_reference_number is not None and booking_reference_number is not "":
				inward_outward_status = "Allocated" + " (" + booking_reference_number + ")"
				allocation_count = allocation_count + 1
			else:
				inward_outward_status = "Free Stock"
				unallocation_count = unallocation_count + 1
			items_data = {"whse":warehouse,"item":item_code,"serial_id":data['serial_no'], 				       						"inward_outward_status": inward_outward_status}
			items_in_stock_list.append(items_data)

	summ_data.append(["Opening Stock", "", "Total:", int(opening_qty)])
	summ_data.append(["Vehicles Inward", "","", ""])
	for data in inward_list:
		summ_data.append([data['whse'], data['item'], data['serial_id'], data['dest_whse']])
	summ_data.append(["", "","", ""])
	summ_data.append(["Total Vehicles Inward ", int(total_vehicles_inward),"", ""])
	summ_data.append(["", "","", ""])

	summ_data.append(["Vehicles Outward", "","", ""])
	for data in outward_list:
		summ_data.append([data['whse'], data['item'], data['serial_id'], data['dest_whse']])
	summ_data.append(["", "","", ""])
	summ_data.append(["Total Vehicles Outward ", int(total_vehicles_outward),"", ""])
	summ_data.append(["", "","", ""])

	summ_data.append(["Vehicles In Stock", "","", ""])
	for data in items_in_stock_list:
		summ_data.append([data['whse'], data['item'], data['serial_id'], data['inward_outward_status']])
	summ_data.append(["", "","", ""])
	summ_data.append(["", "","", ""])

	summ_data.append([warehouse, "Allocated", int(allocation_count), "Unallocated", int(unallocation_count), "Total:", 
	int(allocation_count + unallocation_count)])
	if allocation_count:
		allocation_count = 0
	if unallocation_count:
		unallocation_count = 0
	return columns, summ_data

def get_serial_no_details(serial_id,old_date,vehicle_status):
	warehouse = ""
	if vehicle_status == "outward":
		details = frappe.db.sql(""" select t_warehouse from `tabStock Entry Detail` where serial_no = %s and 
				s_warehouse = 'Truck  - HSR' and modified > '"""+old_date+"""' order by modified""", serial_id, as_dict=1)
		if len(details)!=0:
			warehouse = details[0]['t_warehouse']
	else:
		details = frappe.db.sql(""" select s_warehouse from `tabStock Entry Detail` where serial_no = %s and 
				t_warehouse = 'Truck  - HSR' and modified < '"""+old_date+"""' order by modified desc""", serial_id, as_dict=1)
		if len(details)!=0:
			warehouse = details[0]['s_warehouse']
	return warehouse

def get_sales_invoice_details(voucher_no):
	details = frappe.db.sql(""" select sii.serial_no,sii.item_code,si.customer from `tabSales Invoice` si, `tabSales Invoice Item` sii 					where sii.parent= %s and si.name=sii.parent """, voucher_no, as_dict=1)
	return details

def get_delivery_details(voucher_no):
	details = frappe.db.sql(""" select dni.serial_no,dni.item_code,dn.customer from `tabDelivery Note Item` dni,`tabDelivery Note` dn 
				where dni.parent= %s and dn.name=dni.parent""", voucher_no, as_dict=1)
	return details

def get_destination_warehouse(voucher_no):
	whse = frappe.db.sql(""" select sed.item_code,sed.t_warehouse,se.purpose,sed.s_warehouse,sed.serial_no,sed.modified from 
		`tabStock Entry Detail` sed, `tabStock Entry` se where sed.parent = %s and sed.parent = se.name order by sed.modified""", 			voucher_no, as_dict=1)
	return whse

def get_items_in_stock(filters):
	to_date = str(datetime.date.today())
	to_date = to_date + " " + "23:59:59.999999"
	delivery_date = str(datetime.date.today())
	#date = datetime.datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S.%f")
	#print "to_date--------------", date
	stock_list = frappe.db.sql("""select serial_no,item_code,booking_reference_number,warehouse from `tabSerial No` where 			     warehouse='"""+warehouse+"""' and modified <= '"""+to_date+"""' and delivery_document_no is null or 			     delivery_date > '"""+delivery_date+"""' """, as_dict=1)
	return stock_list


'''
def get_items_in_stock(filters):
	to_date = str(datetime.date.today())
	to_date = to_date + " " + "23:59:59.999999"
	delivery_date = str(datetime.date.today())
	#date = datetime.datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S.%f")
	#print "to_date--------------", date
	stock_list = frappe.db.sql("""select serial_no from `tabStock Entry Detail` where t_warehouse ='"""+warehouse+"""' and 				     serial_no not in (select serial_no from `tabStock Entry Detail` where s_warehouse ='"""+warehouse+"""' and 			     modified <= '"""+to_date+"""') and serial_no in(select serial_no from `tabSerial No` where 
			     delivery_document_no is null or delivery_date > '"""+delivery_date+"""')""", as_dict=1)
	#print "---------------stock_list:", stock_list
	return stock_list
'''
 
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

def get_customer(serial_no):
	details = frappe.db.sql(""" select customer_name,booking_reference_number,vehicle_status,item_code,delivery_date from `tabSerial No` 					where serial_no = %s""", serial_no, as_dict=1)
	return details


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
	from_date = datetime.date.today()
	to_date = datetime.date.today()
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join(['"' + frappe.db.escape(i,percent=False) + '"' for i in items]))
	return frappe.db.sql("""select sle.posting_date,
			sle.item_code, sle.warehouse, sle.actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, sle.serial_no, sn.vehicle_status, sn.booking_reference_number
		from `tabStock Ledger Entry` sle, `tabSerial No` sn where sle.serial_no = sn.name and posting_date >= %s and posting_date <= %s and sle.warehouse = %s order by item_code asc, sle.actual_qty desc""", (from_date, to_date, filters.get("warehouse")), as_dict=1)

def get_opening_balance(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = ' and sle.item_code in ({})'\
			.format(', '.join(['"' + frappe.db.escape(i, percent=False) + '"' for i in items]))

	conditions = get_conditions(filters)

	return frappe.db.sql("""
		select
			sle.item_code, warehouse, sle.posting_date, sle.actual_qty, sle.valuation_rate, sle.serial_no,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index)
		where sle.docstatus < 2 %s %s
		order by sle.posting_date, sle.posting_time, sle.name""" %
		(item_conditions_sql, conditions), as_dict=1)

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

def get_conditions(filters):
	conditions = ""
	from_date = datetime.datetime.now()
	to_date = datetime.date.today()
	if to_date:
		conditions += " and sle.posting_date <= '%s'" % (to_date)
	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse",
			filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt)

	return conditions
