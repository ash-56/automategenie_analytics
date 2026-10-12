import frappe
from frappe import _

@frappe.whitelist()
def get_analytics(filters=None):
    import json
    filters = json.loads(filters) if isinstance(filters, str) else (filters or {})
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    region = filters.get("region")
    product = filters.get("product")
    sales_person = filters.get("sales_person")

    cond = "WHERE 1=1"
    vals = {}
    if from_date: cond += " AND posting_date >= %(from_date)s"; vals["from_date"]=from_date
    if to_date: cond += " AND posting_date <= %(to_date)s"; vals["to_date"]=to_date
    if region: cond += " AND region = %(region)s"; vals["region"]=region
    if product: cond += " AND product = %(product)s"; vals["product"]=product
    if sales_person: cond += " AND sales_person = %(sales_person)s"; vals["sales_person"]=sales_person

    def q(sql): return frappe.db.sql(sql, vals, as_dict=1)

    # KPIs
    total_leads = frappe.db.count("AG Lead")
    total_customers = frappe.db.count("AG Customer")
    total_quot = frappe.db.count("AG Quotation")
    total_so = frappe.db.count("AG Sales Order")
    total_del = frappe.db.count("AG Delivery")
    total_rating = frappe.db.count("Customer Rating")

    lead_conv = round(total_customers/total_leads*100,1) if total_leads else 0
    quot_conv = round(total_so/total_quot*100,1) if total_quot else 0

    sales_data = q(f"SELECT COALESCE(SUM(order_value),0) as total, AVG(order_value) as avg FROM `tabAG Sales Order` {cond}")
    total_sales = sales_data[0].total or 0
    avg_order = round(sales_data[0].avg or 0,2)

    del_stats = frappe.db.sql(f"SELECT COUNT(*) as total, SUM(CASE WHEN delivery_status='Delayed' THEN 1 ELSE 0 END) as delayed, AVG(DATEDIFF(actual_delivery_date, promised_delivery_date)) as avg_delay FROM `tabAG Delivery` {cond}", vals, as_dict=1)[0]
    del_completion = round((1 - (del_stats.delayed or 0)/(del_stats.total or 1))*100,1)

    rating_stats = frappe.db.sql(f"""
        SELECT AVG(rating) as avg_rating,
        SUM(CASE WHEN rating <=2 THEN 1 ELSE 0 END) as low_rated
        FROM `tabCustomer Rating` r JOIN `tabAG Delivery` d ON r.delivery = d.name {cond.replace('posting_date','d.posting_date')}
    """, vals, as_dict=1)[0]

    # Charts
    sales_by_month = q(f"SELECT DATE_FORMAT(posting_date,'%%Y-%%m') as month, SUM(order_value) as value, COUNT(*) as cnt FROM `tabAG Sales Order` {cond} GROUP BY month ORDER BY month")
    sales_by_region = q(f"SELECT region, SUM(order_value) as value, COUNT(*) as cnt FROM `tabAG Sales Order` {cond} GROUP BY region")
    sales_by_product = q(f"SELECT product, SUM(order_value) as value FROM `tabAG Sales Order` {cond} GROUP BY product")
    sales_by_rep = q(f"SELECT sales_person, SUM(order_value) as value, COUNT(*) as cnt FROM `tabAG Sales Order` {cond} GROUP BY sales_person")
    delivery_by_status = frappe.db.sql(f"SELECT delivery_status, COUNT(*) as cnt FROM `tabAG Delivery` {cond} GROUP BY delivery_status", vals, as_dict=1)
    rating_dist = frappe.db.sql("SELECT rating, COUNT(*) as cnt FROM `tabCustomer Rating` GROUP BY rating ORDER BY rating", as_dict=1)
    low_rated_products = frappe.db.sql(f"""
        SELECT d.product, AVG(r.rating) as avg_rating, COUNT(*) as cnt
        FROM `tabCustomer Rating` r JOIN `tabAG Delivery` d ON r.delivery=d.name
        {cond.replace('posting_date','d.posting_date')} GROUP BY d.product HAVING avg_rating < 3 ORDER BY avg_rating
    """, vals, as_dict=1)
    delay_vs_rating = frappe.db.sql(f"""
        SELECT CASE WHEN d.delivery_status='Delayed' THEN 'Delayed' ELSE 'On Time' END as status, AVG(r.rating) as avg_rating
        FROM `tabCustomer Rating` r JOIN `tabAG Delivery` d ON r.delivery=d.name GROUP BY status
    """, as_dict=1)

    return {
        "kpi": {
            "total_leads": total_leads, "total_customers": total_customers, "total_quot": total_quot,
            "total_so": total_so, "total_del": total_del, "total_rating": total_rating,
            "lead_conv": lead_conv, "quot_conv": quot_conv,
            "total_sales": total_sales, "avg_order": avg_order,
            "del_completion": del_completion, "avg_delay": round(del_stats.avg_delay or 0,1),
            "avg_rating": round(rating_stats.avg_rating or 0,2), "low_rated": rating_stats.low_rated or 0,
            "delayed_count": del_stats.delayed or 0
        },
        "charts": {
            "sales_by_month": sales_by_month, "sales_by_region": sales_by_region,
            "sales_by_product": sales_by_product, "sales_by_rep": sales_by_rep,
            "delivery_by_status": delivery_by_status, "rating_dist": rating_dist,
            "low_rated_products": low_rated_products, "delay_vs_rating": delay_vs_rating
        }
    }

@frappe.whitelist()
def get_ai_insights(question=None, filters=None):
    # Aggregated metrics as context - never send 60k rows
    data = get_analytics(filters)
    kpi = data["kpi"]
    context = f"""
    Business Metrics: Leads={kpi['total_leads']}, Customers={kpi['total_customers']}, Lead Conv={kpi['lead_conv']}%, Quot Conv={kpi['quot_conv']}%,
    Total Sales={kpi['total_sales']}, Avg Order={kpi['avg_order']}, Delayed={kpi['delayed_count']}, Del Completion={kpi['del_completion']}%,
    Avg Delay={kpi['avg_delay']} days, Avg Rating={kpi['avg_rating']}, Low Rated={kpi['low_rated']}
    Charts: {data['charts']['sales_by_region']}, {data['charts']['low_rated_products']}, {data['charts']['delay_vs_rating']}
    """
    # Fallback rule-based insights
    insights = []
    if kpi['delayed_count'] > kpi['total_del']*0.2:
        insights.append(f"⚠️ {kpi['delayed_count']} deliveries delayed ({100-kpi['del_completion']:.1f}%). Investigate logistics in regions with high delays.")
    if data['charts']['low_rated_products']:
        for p in data['charts']['low_rated_products'][:2]:
            insights.append(f"🔍 Low rating for {p['product']}: {p['avg_rating']:.1f} avg. Check quality/delivery for this product.")
    if data['charts']['delay_vs_rating']:
        insights.append("📊 Delayed deliveries correlate with lower ratings. Improving on-time delivery may boost ratings.")

    # Question handling
    answer = "Based on aggregated metrics"
    if question:
        q_lower = question.lower()
        if "delayed" in q_lower and "region" in q_lower:
            top = sorted(data['charts']['sales_by_region'], key=lambda x: x['cnt'], reverse=True)
            answer = f"Region analysis: Check delivery data by region. Highest order volume in {top[0]['region'] if top else 'N/A'} may have more delays."
        elif "low rating" in q_lower or "low rated" in q_lower:
            answer = f"Low rated products: {', '.join([f\"{p['product']} ({p['avg_rating']:.1f})\" for p in data['charts']['low_rated_products']]) or 'None <3 stars'}"
        else:
            answer = f"Q: {question} | A: Metrics show {kpi['del_completion']}% delivery success, {kpi['avg_rating']} avg rating. See charts for breakdown."

    return {"context_used": context[:500], "insights": insights, "answer": answer, "kpi": kpi}
