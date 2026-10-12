import frappe, random
from datetime import datetime, timedelta
from frappe.utils import nowdate

REGIONS = ["North", "South", "East", "West", "Central"]
PRODUCTS = ["Product A", "Product B", "Product C", "Service X", "Service Y"]
SALES = ["Rahul", "Priya", "Amit", "Sneha", "Vikram"]
FEEDBACKS = ["Good service", "Delayed but ok", "Excellent!", "Poor delivery", "Average experience", "Will order again"]

def random_date(start_days_ago=365):
    days = random.randint(0, start_days_ago)
    return (datetime.now() - timedelta(days=days)).date()

def generate():
    frappe.init(site="dev.localhost")
    frappe.connect()
    frappe.set_user("Administrator")

    # Clear existing to avoid duplicates - comment if you want to keep
    # for dt in ["Customer Rating", "AG Delivery", "AG Sales Order", "AG Quotation", "AG Customer", "AG Lead"]:
    # frappe.db.delete(dt)
    # frappe.db.commit()

    print("Starting 60k generation...")

    # 1. AG LEAD - 10k
    leads = []
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Leads: {i}/10000")
        # avoid duplicate check
        name = f"Lead {i+1}"
        if frappe.db.exists("AG Lead", {"lead_name": name}):
            continue
        doc = frappe.get_doc({
            "doctype": "AG Lead",
            "lead_name": f"{random.choice(['John','Sara','Mike','Anita','Raj'])} {random.randint(100,9999)}",
            "company_name": f"Company {random.randint(1,5000)}",
            "email": f"user{i}@test.com",
            "region": random.choice(REGIONS),
            "product_interest": random.choice(PRODUCTS),
            "sales_person": random.choice(SALES),
            "lead_status": random.choices(["Open","Converted","Lost"], weights=[2,6,2])[0],
            "converted": 0,
            "posting_date": random_date()
        })
        doc.insert(ignore_permissions=True)
        leads.append(doc.name)

    # Mark converted
    frappe.db.sql("UPDATE `tabAG Lead` SET converted=1 WHERE lead_status='Converted'")
    frappe.db.commit()
    print(f"✅ Leads Done: {len(leads)}")

    # Get all converted leads
    converted_leads = frappe.get_all("AG Lead", filters={"lead_status": "Converted"}, pluck="name")
    if not converted_leads:
        converted_leads = leads[:7000]

    # 2. AG CUSTOMER - 10k
    customers = []
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Customers: {i}/10000")
        lead = random.choice(converted_leads) if i < len(converted_leads) else None
        lead_doc = frappe.get_doc("AG Lead", lead) if lead else None
        doc = frappe.get_doc({
            "doctype": "AG Customer",
            "customer_name": f"Customer {i+1}",
            "ag_lead": lead,
            "region": lead_doc.region if lead_doc else random.choice(REGIONS),
            "sales_person": lead_doc.sales_person if lead_doc else random.choice(SALES),
            "is_repeat": random.choices([0,1], weights=[8,2])[0],
            "posting_date": random_date(300)
        })
        doc.insert(ignore_permissions=True)
        customers.append(doc.name)
    frappe.db.commit()
    print("✅ Customers Done")

    # 3. AG QUOTATION - 10k
    quotations = []
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Quotations: {i}/10000")
        cust = random.choice(customers)
        cust_doc = frappe.get_doc("AG Customer", cust)
        doc = frappe.get_doc({
            "doctype": "AG Quotation",
            "ag_customer": cust,
            "ag_lead": cust_doc.ag_lead,
            "region": cust_doc.region,
            "product": random.choice(PRODUCTS),
            "sales_person": cust_doc.sales_person,
            "quotation_value": random.randint(5000, 200000),
            "status": random.choices(["Draft","Sent","Converted","Lost"], weights=[1,2,6,1])[0],
            "posting_date": random_date(250)
        })
        doc.insert(ignore_permissions=True)
        quotations.append(doc.name)
    frappe.db.commit()
    print("✅ Quotations Done")

    # 4. AG SALES ORDER - 10k
    converted_quots = frappe.get_all("AG Quotation", filters={"status":"Converted"}, pluck="name")
    if len(converted_quots) < 7000:
        converted_quots = quotations[:7000]

    sales_orders = []
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Sales Orders: {i}/10000")
        quot = random.choice(converted_quots) if i < len(converted_quots) else random.choice(quotations)
        quot_doc = frappe.get_doc("AG Quotation", quot)
        doc = frappe.get_doc({
            "doctype": "AG Sales Order",
            "ag_quotation": quot,
            "ag_customer": quot_doc.ag_customer,
            "region": quot_doc.region,
            "product": quot_doc.product,
            "sales_person": quot_doc.sales_person,
            "order_value": quot_doc.quotation_value,
            "status": "Confirmed",
            "posting_date": random_date(200)
        })
        doc.insert(ignore_permissions=True)
        sales_orders.append(doc.name)
    frappe.db.commit()
    print("✅ Sales Orders Done")

    # 5. AG DELIVERY - 10k
    deliveries = []
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Deliveries: {i}/10000")
        so = random.choice(sales_orders)
        so_doc = frappe.get_doc("AG Sales Order", so)
        promised = random_date(180)
        is_delayed = random.choices([0,1], weights=[7,3])[0]
        delay = random.randint(1,15) if is_delayed else 0
        actual = promised + timedelta(days=delay) if is_delayed else promised

        doc = frappe.get_doc({
            "doctype": "AG Delivery",
            "ag_sales_order": so,
            "ag_customer": so_doc.ag_customer,
            "region": so_doc.region,
            "product": so_doc.product,
            "sales_person": so_doc.sales_person,
            "delivery_status": "Delayed" if is_delayed else "On Time",
            "promised_date": promised,
            "actual_delivery_date": actual,
            "delay_days": delay,
            "posting_date": actual
        })
        doc.insert(ignore_permissions=True)
        deliveries.append(doc.name)
    frappe.db.commit()
    print("✅ Deliveries Done")

    # 6. CUSTOMER RATING - 10k
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Ratings: {i}/10000")
        deli = random.choice(deliveries)
        deli_doc = frappe.get_doc("AG Delivery", deli)
        # Low rating if delayed
        if deli_doc.delivery_status == "Delayed":
            rating = random.choices([1,2,3,4,5], weights=[2,3,2,2,1])[0]
        else:
            rating = random.choices([1,2,3,4,5], weights=[1,1,2,3,3])[0]

        doc = frappe.get_doc({
            "doctype": "Customer Rating",
            "ag_delivery": deli,
            "ag_customer": deli_doc.ag_customer,
            "ag_sales_order": deli_doc.ag_sales_order,
            "region": deli_doc.region,
            "product": deli_doc.product,
            "sales_person": deli_doc.sales_person,
            "rating": rating,
            "feedback": random.choice(FEEDBACKS),
            "posting_date": random_date(150)
        })
        doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("✅ Ratings Done - 60k COMPLETE!")

    # Final counts
    for dt in ["AG Lead", "AG Customer", "AG Quotation", "AG Sales Order", "AG Delivery", "Customer Rating"]:
        count = frappe.db.count(dt)
        print(f"{dt}: {count}")

    frappe.destroy()

if __name__ == "__main__":
    generate()
