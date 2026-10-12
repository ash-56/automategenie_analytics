# AG Analytics Dashboard - 60k Records

## Overview
Frappe-based analytics dashboard processing 60k+ records across Lead, Customer, Quotation, Sales Order, Delivery, Customer Rating.

## Features Implemented
- 6 KPIs: Lead Conversion 100%, Quotation->SO 100%, Total Sales Rs.2723.4L, Delivery Success, Avg Rating 2.98, 60k Records Verified
- 7 Charts: Sales by Month (Line), Sales by Region (Bar), Sales by Product (Pie), Sales by Rep (Bar), Delivery Status, Rating Distribution, Delay vs Rating
- Dynamic Filters: From Date, To Date, Region, Product, Sales Rep with Apply button
- AI Insights: Natural language Q&A - "Which region has most delayed deliveries?"

## Setup
bench --site dev.localhost install-app automategenie_analytics
bench --site dev.localhost migrate
bench build --app automategenie_analytics
bench --site dev.localhost clear-cache

## Access
http://dev.localhost:8000/app/ag-analytics-dashboa

## Tech Stack
Frappe Framework, MariaDB, Frappe Charts, Python REST API

## Data Model
AG Lead (10k) -> AG Customer (10k) -> AG Quotation (10k) -> AG Sales Order (10k) -> AG Delivery (10k) -> Customer Rating (10k)

## 📊 60k Proof

| DocType | Count |
| AG Lead | 10000 |
| AG Customer | 10000 |
| AG Quotation | 10000 |
| AG Sales Order | 10000 |
| AG Delivery | 10000 |
| AG Customer Rating | 10000 |

<img width="1787" height="478" alt="photo3" src="https://github.com/user-attachments/assets/25e99730-a2fb-4c45-8c63-9197904687ec" />
<img width="1787" height="478" alt="photo3" src="https://github.com/user-attachments/assets/d97494cf-661b-449d-9032-b1a50af59b55" />
<img width="1756" height="761" alt="photo2" src="https://github.com/user-attachments/assets/81fa32d0-eaff-487a-b32d-9c055d0c28bf" />

