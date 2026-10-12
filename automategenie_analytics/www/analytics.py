import frappe

def get_context(context):
    context.analytics = frappe.call('automategenie_analytics.tasks.get_analytics')
    return context
