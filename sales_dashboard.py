import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("RawData.csv")

    # --- Standardize column names ---
    df.columns = df.columns.str.strip()

    rename_map = {
        "CHANNEL": "Channel",
        "Sales Executive": "Salesman",
        "Sub Category": "SubCategory",
        "Part Number": "PartNo",
        "Amount": "Value"
    }
    df = df.rename(columns=rename_map)

    # --- Type column ---
    df["Type"] = df["Type"].astype(str).str.upper().str.strip()

    # --- Numeric value ---
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)

    # 🔴 Force returns to be negative
    df.loc[df["Type"] == "RETURN", "Value"] = -df.loc[df["Type"] == "RETURN", "Value"].abs()

    # --- Date ---
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df

df = load_data()

# =========================
# GLOBAL FILTERS
# =========================
st.title("📊 Sales Dashboard")

col1, col2, col3, col4 = st.columns(4)

start_date = col1.date_input("Start Date", df["Date"].min())
end_date = col2.date_input("End Date", df["Date"].max())

type_filter = col3.selectbox("Type", ["BOTH", "SALE", "RETURN"])

channel_filter = col4.multiselect(
    "Channel",
    sorted(df["Channel"].dropna().unique())
)

# --- Apply date filter ---
filtered_df = df[(df["Date"] >= pd.to_datetime(start_date)) &
                 (df["Date"] <= pd.to_datetime(end_date))]

# --- Apply type filter ---
if type_filter != "BOTH":
    filtered_df = filtered_df[filtered_df["Type"] == type_filter]

# --- Apply channel filter ---
if channel_filter:
    filtered_df = filtered_df[filtered_df["Channel"].isin(channel_filter)]

# =========================
# KPI CALCULATIONS
# =========================
sales_df = filtered_df[filtered_df["Type"] == "SALE"]
return_df = filtered_df[filtered_df["Type"] == "RETURN"]

net_revenue = filtered_df["Value"].sum()
sales_value = sales_df["Value"].sum()
return_value = return_df["Value"].sum()
sales_volume = sales_df["Qty"].sum() if "Qty" in sales_df.columns else 0

k1, k2, k3, k4 = st.columns(4)

k1.metric("Net Revenue", f"OMR {net_revenue:,.2f}")
k2.metric("Sale Value", f"OMR {sales_value:,.2f}")
k3.metric("Return Value", f"OMR {return_value:,.2f}")
k4.metric("Sale Volume", f"{sales_volume:,.0f}")

# =========================
# DONUT CHART DATA LOGIC
# =========================
if type_filter == "SALE":
    donut_df = sales_df
elif type_filter == "RETURN":
    donut_df = return_df
else:
    donut_df = sales_df  # default: show SALES share for BOTH

# =========================
# CHARTS ROW
# =========================
c1, c2 = st.columns(2)

# --- Category Share ---
if not donut_df.empty:
    cat_share = donut_df.groupby("Category")["Value"].sum().abs().reset_index()
    fig_cat = px.pie(cat_share, values="Value", names="Category", hole=0.6)
    c1.subheader("Category Share")
    c1.plotly_chart(fig_cat, use_container_width=True)
else:
    c1.info("No data for selected filters")

# --- Channel Share ---
if not donut_df.empty:
    ch_share = donut_df.groupby("Channel")["Value"].sum().abs().reset_index()
    fig_ch = px.pie(ch_share, values="Value", names="Channel", hole=0.6)
    c2.subheader("Channel Share")
    c2.plotly_chart(fig_ch, use_container_width=True)
else:
    c2.info("No data for selected filters")

# =========================
# SALESMAN PERFORMANCE SECTION
# =========================
st.markdown("---")
st.subheader("Sales Executive Performance")

s_col1, s_col2 = st.columns(2)

salesman_filter = s_col1.multiselect(
    "Salesman",
    sorted(filtered_df["Salesman"].dropna().unique())
)

salesman_df = filtered_df.copy()

if salesman_filter:
    salesman_df = salesman_df[salesman_df["Salesman"].isin(salesman_filter)]

salesman_perf = (
    salesman_df.groupby("Salesman")["Value"]
    .sum()
    .reset_index()
    .sort_values("Value", ascending=False)
)

fig_salesman = px.bar(
    salesman_perf,
    x="Value",
    y="Salesman",
    orientation="h"
)

s_col1.plotly_chart(fig_salesman, use_container_width=True)

# =========================
# FAST MOVING SKU SECTION
# =========================
st.subheader("Fast Moving SKU")

f1, f2, f3, f4 = st.columns(4)

sku_start = f1.date_input("SKU Start Date", df["Date"].min(), key="sku_start")
sku_end = f2.date_input("SKU End Date", df["Date"].max(), key="sku_end")

sku_category = f3.multiselect(
    "Category",
    sorted(df["Category"].dropna().unique())
)

sku_subcat = f4.multiselect(
    "Sub Category",
    sorted(df["SubCategory"].dropna().unique())
)

# 🔴 NEW CHANNEL FILTER FOR FAST SKU
sku_channel = st.multiselect(
    "Channel (SKU)",
    sorted(df["Channel"].dropna().unique())
)

sku_df = df[
    (df["Date"] >= pd.to_datetime(sku_start)) &
    (df["Date"] <= pd.to_datetime(sku_end))
]

sku_df = sku_df[sku_df["Type"] == "SALE"]

if sku_category:
    sku_df = sku_df[sku_df["Category"].isin(sku_category)]

if sku_subcat:
    sku_df = sku_df[sku_df["SubCategory"].isin(sku_subcat)]

if sku_channel:
    sku_df = sku_df[sku_df["Channel"].isin(sku_channel)]

fast_sku = (
    sku_df.groupby(["PartNo", "Category", "SubCategory"])["Qty"]
    .sum()
    .reset_index()
    .sort_values("Qty", ascending=False)
    .head(10)
)

st.dataframe(fast_sku, use_container_width=True)