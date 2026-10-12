import frappe
import random
import logging
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGIONS = ["Chennai", "Mumbai", "Delhi", "Bangalore", "Coimbatore", "Hyderabad"]
PRODUCTS = ["Genie Bot", "Automation Kit", "Sensor X", "Widget A", "Widget B"]
SALES_PERSONS = ["Ashmad", "Priya", "Rahul", "Sales Team 1", "Sales Team 2"]
SOURCES = ["Website", "Referral", "Cold Call", "Campaign"]

def generate_all_data(count=10000):
    count = int(count)
    logger.info(f"Starting generation of {count} per doctype")
    for dt in ["AG Delivery", "AG Sales Order", "AG Quotation", "AG Customer", "AG Lead", "Customer Rating"]:
        try:
            frappe.db.sql(f"DELETE FROM `tab{dt}`")
            frappe.db.commit()
        except Exception as e:
            print(f"Clear {dt} failed: {e}")

    leads = []
    customers = []
    print(f"Generating {count} Leads...")
    for i in range(count):
        try:
            doc = frappe.get_doc({
                "doctype": "AG Lead",
                "lead_name": fake.name(),
                "email": f"lead_{i}_{fake.email()}",
                "region": random.choice(REGIONS),
                "source": random.choice(SOURCES),
                "sales_person": random.choice(SALES_PERSONS),
                "status": random.choice(["Converted", "Open", "Lost"]),
                "posting_date": (datetime.now() - timedelta(days=random.randint(0, 180))).date()
            })
            doc.insert(ignore_permissions=True)
            leads.append(doc.name)
            if i % 500 == 0:
                frappe.db.commit()
                print(f"Leads {i}/{count}")
        except Exception as e:
            print(f"Lead {i} failed: {e}")
    frappe.db.commit()

    print(f"Generating {count} Customers...")
    for i in range(count):
        try:
            doc = frappe.get_doc({
                "doctype": "AG Customer",
                "customer_name": fake.company() if i % 2 == 0 else fake.name(),
                "lead": random.choice(leads) if leads else "",
                "region": random.choice(REGIONS),
                "sales_person": random.choice(SALES_PERSONS),
                "is_repeat": 1 if random.random() > 0.7 else 0,
                "posting_date": (datetime.now() - timedelta(days=random.randint(0, 150))).date()
            })
            doc.insert(ignore_permissions=True)
            customers.append(doc.name)
            if i % 500 == 0:
                frappe.db.commit()
                print(f"Customers {i}/{count}")
        except Exception as e:
            print(f"Customer {i} failed: {e}")
    frappe.db.commit()

    print(f"Generating chain {count}...")
    for i in range(count):
        try:
            cust = random.choice(customers)
            region = frappe.db.get_value("AG Customer", cust, "region") or random.choice(REGIONS)
            product = random.choice(PRODUCTS)
            value = random.randint(5000, 100000)
            sales_person = random.choice(SALES_PERSONS)
            post_date = (datetime.now() - timedelta(days=random.randint(0, 120))).date()

            q = frappe.get_doc({
                "doctype": "AG Quotation",
                "customer": cust,
                "product": product,
                "region": region,
                "sales_person": sales_person,
                "grand_total": value,
                "status": random.choice(["Ordered", "Lost", "Open"]),
                "posting_date": post_date
            })
            q.insert(ignore_permissions=True)

            if q.status == "Ordered" or random.random() > 0.2:
                so = frappe.get_doc({
                    "doctype": "AG Sales Order",
                    "quotation": q.name,
                    "customer": cust,
                    "product": product,
                    "region": region,
                    "sales_person": sales_person,
                    "grand_total": value,
                    "posting_date": post_date
                })
                so.insert(ignore_permissions=True)

                delay = random.randint(-2, 15)
                delivery_status = "Delayed" if delay > 3 else "On Time"
                dl_date = (datetime.strptime(str(post_date), "%Y-%m-%d") + timedelta(days=random.randint(2, 20))).date()

                dl = frappe.get_doc({
                    "doctype": "AG Delivery",
                    "sales_order": so.name,
                    "customer": cust,
                    "region": region,
                    "product": product,
                    "delivery_status": delivery_status,
                    "delay_days": max(0, delay),
                    "posting_date": dl_date
                })
                dl.insert(ignore_permissions=True)

                rating = 5 if delay <= 0 else random.randint(1, 4) if delay > 5 else random.randint(3, 5)
                rt = frappe.get_doc({
                    "doctype": "Customer Rating",
                    "customer": cust,
                    "product": product,
                    "region": region,
                    "sales_person": sales_person,
                    "rating": rating,
                    "delivery_delay_days": max(0, delay),
                    "feedback": random.choice(["Great", "Late delivery", "Average", "Excellent service", "Product issue"]),
                    "posting_date": dl_date
                })
                rt.insert(ignore_permissions=True)

            if i % 500 == 0:
                frappe.db.commit()
                print(f"Chain {i}/{count}")
        except Exception as e:
            print(f"Chain {i} failed: {e}")

    frappe.db.commit()
    counts = {}
    for dt in ["AG Lead", "AG Customer", "AG Quotation", "AG Sales Order", "AG Delivery", "Customer Rating"]:
        counts[dt] = frappe.db.count(dt)
    print(f"Final counts: {counts}")
    return counts

@frappe.whitelist()
def get_analytics():
    region_rating = frappe.db.sql("SELECT region, AVG(rating) as avg_rating, COUNT(*) as cnt FROM `tabCustomer Rating` GROUP BY region", as_dict=True)
    product_rating = frappe.db.sql("SELECT product, AVG(rating) as avg_rating, COUNT(*) as cnt FROM `tabCustomer Rating` GROUP BY product", as_dict=True)
    delay_by_region = frappe.db.sql("SELECT region, AVG(delay_days) as avg_delay, COUNT(*) as cnt FROM `tabAG Delivery` GROUP BY region ORDER BY avg_delay DESC", as_dict=True)
    lead_conv = frappe.db.sql("SELECT status, COUNT(*) as cnt FROM `tabAG Lead` GROUP BY status", as_dict=True)
    return {"region_rating": region_rating, "product_rating": product_rating, "delay_by_region": delay_by_region, "lead_conv": lead_conv, "counts": {dt: frappe.db.count(dt) for dt in ["AG Lead","AG Customer","AG Quotation","AG Sales Order","AG Delivery","Customer Rating"]}}

@frappe.whitelist()
def ai_insights(query=""):
    query = query.lower()
    if "delay" in query:
        data = frappe.db.sql("SELECT region, AVG(delay_days) as avg_delay FROM `tabAG Delivery` GROUP BY region ORDER BY avg_delay DESC", as_dict=True)
        return {"facts": data, "insight": f"Most delayed region is {data[0]['region']} with {data[0]['avg_delay']:.1f} days avg delay. Hypothesis: Logistics issue in that region.", "type":"fact+hypothesis"}
    elif "rating" in query:
        data = frappe.db.sql("SELECT product, AVG(rating) as avg_rating FROM `tabCustomer Rating` GROUP BY product ORDER BY avg_rating ASC", as_dict=True)
        return {"facts": data, "insight": f"Lowest rated product is {data[0]['product']} with {data[0]['avg_rating']:.2f}. Investigate product quality/delivery.", "type":"fact+hypothesis"}
    else:
        analytics = get_analytics()
        return {"facts": analytics, "insight": "Overall business is stable. Use queries like 'Which region had most delayed deliveries last month?'", "type":"fact+hypothesis"}
