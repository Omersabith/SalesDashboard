import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(layout="wide", page_title="Sales Dashboard")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("RawData.csv")
    except FileNotFoundError:
        st.error("RawData.csv not found. Please ensure the file is in the same directory.")
        return pd.DataFrame()

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

    # --- Type column normalization ---
    df["Type"] = df["Type"].astype(str).str.upper().str.strip()

    # --- Numeric values ---
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)
    df["Qty"] = pd.to_numeric(df.get("Qty", 0), errors="coerce").fillna(0)

    # 🔴 Force returns to be negative for correct revenue calculation
    df.loc[df["Type"] == "RETURN", "Value"] = -df.loc[df["Type"] == "RETURN", "Value"].abs()

    # --- Date Parsing (FIXED FOR DD/MM/YYYY) ---
    # Using dayfirst=True ensures 09/01/2025 is read as Sept 1st, not Jan 9th
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    
    # Drop rows with invalid dates to prevent errors in filters
    df = df.dropna(subset=["Date"])

    return df

df = load_data()

if df.empty:
    st.stop()

# =========================
# GLOBAL FILTERS
# =========================
st.title("📊 Sales Dashboard")

col1, col2, col3, col4 = st.columns(4)

# Date inputs
start_date = col1.date_input("Start Date", df["Date"].min())
end_date = col2.date_input("End Date", df["Date"].max())

type_filter = col3.selectbox("Type", ["BOTH", "SALE", "RETURN"])

channel_options = sorted(df["Channel"].dropna().unique())
channel_filter = col4.multiselect("Channel", channel_options)

# --- Apply Global Filters ---
# Convert date_input (date) to pandas timestamp (datetime64) for comparison
mask = (df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))

if type_filter != "BOTH":
    mask &= (df["Type"] == type_filter)

if channel_filter:
    mask &= (df["Channel"].isin(channel_filter))

filtered_df = df[mask]

# =========================
# KPI CALCULATIONS
# =========================
sales_df = filtered_df[filtered_df["Type"] == "SALE"]
return_df = filtered_df[filtered_df["Type"] == "RETURN"]

net_revenue = filtered_df["Value"].sum()
sales_value = sales_df["Value"].sum()
return_value = return_df["Value"].sum()
sales_volume = sales_df["Qty"].sum()

k1, k2, k3, k4 = st.columns(4)

k1.metric("Net Revenue", f"OMR {net_revenue:,.2f}")
k2.metric("Sale Value", f"OMR {sales_value:,.2f}")
k3.metric("Return Value", f"OMR {return_value:,.2f}")
k4.metric("Sale Volume", f"{sales_volume:,.0f}")

# =========================
# CHARTS ROW
# =========================
st.markdown("---")
c1, c2 = st.columns(2)

# Logic: Use absolute values for pie charts so shares are represented correctly
# regardless of negative return values.
chart_data = filtered_df.copy()
chart_data["AbsValue"] = chart_data["Value"].abs()

if not chart_data.empty:
    # Category Share
    cat_share = chart_data.groupby("Category")["AbsValue"].sum().reset_index()
    fig_cat = px.pie(cat_share, values="AbsValue", names="Category", hole=0.6, title="Category Share")
    c1.plotly_chart(fig_cat, use_container_width=True)

    # Channel Share
    ch_share = chart_data.groupby("Channel")["AbsValue"].sum().reset_index()
    fig_ch = px.pie(ch_share, values="AbsValue", names="Channel", hole=0.6, title="Channel Share")
    c2.plotly_chart(fig_ch, use_container_width=True)
else:
    st.info("No data for selected filters")

# =========================
# SALESMAN PERFORMANCE SECTION
# =========================
st.markdown("---")
st.subheader("Sales Executive Performance")

s_col1, s_col2 = st.columns([1, 2])

salesman_options = sorted(filtered_df["Salesman"].dropna().unique())
salesman_filter = s_col1.multiselect("Filter Salesman", salesman_options)

salesman_df = filtered_df.copy()
if salesman_filter:
    salesman_df = salesman_df[salesman_df["Salesman"].isin(salesman_filter)]

salesman_perf = (
    salesman_df.groupby("Salesman")["Value"]
    .sum()
    .reset_index()
    .sort_values("Value", ascending=True) # Ascending for horizontal bar orientation
)

fig_salesman = px.bar(
    salesman_perf,
    x="Value",
    y="Salesman",
    orientation="h",
    color="Value",
    color_continuous_scale="Viridis",
    title="Revenue by Salesman"
)

s_col2.plotly_chart(fig_salesman, use_container_width=True)

# =========================
# FAST MOVING SKU SECTION
# =========================
st.markdown("---")
st.subheader("🔥 Fast Moving SKU")

f1, f2, f3, f4 = st.columns(4)

# SKU specific filters
sku_start = f1.date_input("SKU Start Date", df["Date"].min(), key="sku_start")
sku_end = f2.date_input("SKU End Date", df["Date"].max(), key="sku_end")

sku_category = f3.multiselect("Category", sorted(df["Category"].dropna().unique()))
sku_subcat = f4.multiselect("Sub Category", sorted(df["SubCategory"].dropna().unique()))

# NEW CHANNEL FILTER FOR FAST SKU
sku_channel = st.multiselect("Channel (SKU Filter)", channel_options)

# Filter logic for SKU table (Always filter for SALE type for movement)
sku_mask = (df["Date"] >= pd.to_datetime(sku_start)) & (df["Date"] <= pd.to_datetime(sku_end))
sku_mask &= (df["Type"] == "SALE")

if sku_category:
    sku_mask &= (df["Category"].isin(sku_category))
if sku_subcat:
    sku_mask &= (df["SubCategory"].isin(sku_subcat))
if sku_channel:
    sku_mask &= (df["Channel"].isin(sku_channel))

sku_df = df[sku_mask]

fast_sku = (
    sku_df.groupby(["PartNo", "Category", "SubCategory"])["Qty"]
    .sum()
    .reset_index()
    .sort_values("Qty", ascending=False)
    .head(10)
)

st.dataframe(fast_sku, use_container_width=True)
