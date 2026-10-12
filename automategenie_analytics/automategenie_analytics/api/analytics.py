import frappe, json
def get_cols(dt):
    try: return frappe.db.get_table_columns(dt)
    except: return []
@frappe.whitelist()
def get_analytics(filters=None):
    filters=json.loads(filters) if isinstance(filters,str) else (filters or {})
    vals={}; cond_so="WHERE 1=1"; cond_del="WHERE 1=1"
    for k in ["from_date","to_date","region","product","sales_person"]:
        if not filters.get(k): continue
        if k=="from_date":
            cond_so+=" AND posting_date >= %(from_date)s"; cond_del+=" AND posting_date >= %(from_date)s"; vals[k]=filters[k]
        elif k=="to_date":
            cond_so+=" AND posting_date <= %(to_date)s"; cond_del+=" AND posting_date <= %(to_date)s"; vals[k]=filters[k]
        else:
            cond_so+=f" AND {k} = %({k})s"
            if k in get_cols("AG Delivery"): cond_del+=f" AND {k} = %({k})s"
            vals[k]=filters[k]
    def q(sql): return frappe.db.sql(sql, vals, as_dict=1)
    del_cols=get_cols("AG Delivery")
    status_col="delivery_status" if "delivery_status" in del_cols else ("status" if "status" in del_cols else None)
    total_leads=frappe.db.count("AG Lead"); total_customers=frappe.db.count("AG Customer"); total_quot=frappe.db.count("AG Quotation"); total_so=frappe.db.count("AG Sales Order"); total_del=frappe.db.count("AG Delivery"); total_rating=frappe.db.count("Customer Rating")
    lead_conv=round(total_customers/total_leads*100,1) if total_leads else 0; quot_conv=round(total_so/total_quot*100,1) if total_quot else 0
    sales_data=q(f"SELECT COALESCE(SUM(order_value),0) as total, AVG(order_value) as avg FROM `tabAG Sales Order` {cond_so}"); total_sales=sales_data[0].total or 0; avg_order=round(sales_data[0].avg or 0,2)
    if status_col:
        del_stats=frappe.db.sql(f"SELECT COUNT(*) as total, SUM(CASE WHEN {status_col}='Delayed' THEN 1 ELSE 0 END) as delayed_cnt FROM `tabAG Delivery` {cond_del}", vals, as_dict=1)[0]
        delivery_by_status=frappe.db.sql(f"SELECT {status_col} as delivery_status, COUNT(*) as cnt FROM `tabAG Delivery` {cond_del} GROUP BY {status_col}", vals, as_dict=1)
    else:
        del_stats=frappe.db.sql(f"SELECT COUNT(*) as total, 0 as delayed_cnt FROM `tabAG Delivery` {cond_del}", vals, as_dict=1)[0]
        delivery_by_status=[{"delivery_status":"All","cnt":total_del}]
    del_completion=round((1-(del_stats.delayed_cnt or 0)/(del_stats.total or 1))*100,1)
    rating_stats=frappe.db.sql("SELECT AVG(rating) as avg_rating, SUM(CASE WHEN rating <=2 THEN 1 ELSE 0 END) as low_rated FROM `tabCustomer Rating`", as_dict=1)[0]
    sales_by_month=q(f"SELECT DATE_FORMAT(posting_date,'%%Y-%%m') as month, SUM(order_value) as value FROM `tabAG Sales Order` {cond_so} GROUP BY month ORDER BY month")
    sales_by_region=q(f"SELECT region, SUM(order_value) as value FROM `tabAG Sales Order` {cond_so} GROUP BY region")
    sales_by_product=q(f"SELECT product, SUM(order_value) as value FROM `tabAG Sales Order` {cond_so} GROUP BY product")
    sales_by_rep=q(f"SELECT sales_person, SUM(order_value) as value FROM `tabAG Sales Order` {cond_so} GROUP BY sales_person")
    rating_dist=frappe.db.sql("SELECT rating, COUNT(*) as cnt FROM `tabCustomer Rating` GROUP BY rating ORDER BY rating", as_dict=1)
    delay_vs_rating=[]
    try:
        delay_vs_rating=frappe.db.sql("SELECT CASE WHEN d.status='Delayed' OR d.delivery_status='Delayed' THEN 'Delayed' ELSE 'On Time' END as status, AVG(r.rating) as avg_rating FROM `tabCustomer Rating` r JOIN `tabAG Delivery` d ON r.delivery=d.name GROUP BY status", as_dict=1)
    except: pass
    return {"kpi":{"total_leads":total_leads,"total_customers":total_customers,"total_quot":total_quot,"total_so":total_so,"total_del":total_del,"total_rating":total_rating,"lead_conv":lead_conv,"quot_conv":quot_conv,"total_sales":total_sales,"avg_order":avg_order,"del_completion":del_completion,"avg_rating":round(rating_stats.avg_rating or 0,2),"low_rated":rating_stats.low_rated or 0,"delayed_count":del_stats.delayed_cnt or 0},"charts":{"sales_by_month":sales_by_month,"sales_by_region":sales_by_region,"sales_by_product":sales_by_product,"sales_by_rep":sales_by_rep,"delivery_by_status":delivery_by_status,"rating_dist":rating_dist,"delay_vs_rating":delay_vs_rating,"low_rated_products":[]}}
@frappe.whitelist()
def get_ai_insights(question=None, filters=None):
    data=get_analytics(filters); k=data["kpi"]; insights=[f"Lead conversion {k['lead_conv']}% ({k['total_customers']}/{k['total_leads']})", f"Delivery success {k['del_completion']}% with {k['delayed_count']} delays", f"Avg rating {k['avg_rating']} with {k['low_rated']} low ratings", f"Total sales Rs.{k['total_sales']/100000:.1f}L from {k['total_so']} orders"]
    ans="AI Summary of all KPIs"; qq=(question or "").lower()
    if "delay" in qq: ans=f"Most delays: {k['delayed_count']} cases, Success {k['del_completion']}%"
    elif question: ans=f"Answer to '{question}': Analyzed {k['total_del']} deliveries"
    return {"insights":insights, "answer":ans}
