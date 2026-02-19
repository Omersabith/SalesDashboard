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
        st.error("RawData.csv not found.")
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

    # --- Data Cleaning ---
    df["Type"] = df["Type"].astype(str).str.upper().str.strip()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)
    df["Qty"] = pd.to_numeric(df.get("Qty", 0), errors="coerce").fillna(0)

    # 🔴 Force returns to be negative for accurate revenue calculation
    df.loc[df["Type"] == "RETURN", "Value"] = -df.loc[df["Type"] == "RETURN", "Value"].abs()

    # --- Date Parsing (FIXED FOR DD/MM/YYYY) ---
    # dayfirst=True ensures "09/01/2025" is read as Sept 1st, not Jan 9th.
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])

    # --- Create a Month-Year timestamp for the trend graph ---
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()

    return df

df = load_data()

if df.empty:
    st.stop()

# =========================
# GLOBAL FILTERS (All requested filters)
# =========================
st.title("📊 Sales Dashboard")

# Filter Layout (Two rows)
f_row1 = st.columns(4)
f_row2 = st.columns(4)

# Row 1 Filters
start_date = f_row1[0].date_input("Start Date", df["Date"].min())
end_date = f_row1[1].date_input("End Date", df["Date"].max())
type_filter = f_row1[2].selectbox("Type", ["BOTH", "SALE", "RETURN"])
channel_filter = f_row1[3].multiselect("Channel", sorted(df["Channel"].dropna().unique()))

# Row 2 Filters
salesman_filter = f_row2[0].multiselect("Sales Executive", sorted(df["Salesman"].dropna().unique()))
cat_filter = f_row2[1].multiselect("Category", sorted(df["Category"].dropna().unique()))
subcat_filter = f_row2[2].multiselect("Sub Category", sorted(df["SubCategory"].dropna().unique()))
part_filter = f_row2[3].multiselect("Part Number", sorted(df["PartNo"].dropna().unique()))

# --- Apply All Filters ---
mask = (df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))

if type_filter != "BOTH":
    mask &= (df["Type"] == type_filter)
if channel_filter:
    mask &= (df["Channel"].isin(channel_filter))
if salesman_filter:
    mask &= (df["Salesman"].isin(salesman_filter))
if cat_filter:
    mask &= (df["Category"].isin(cat_filter))
if subcat_filter:
    mask &= (df["SubCategory"].isin(subcat_filter))
if part_filter:
    mask &= (df["PartNo"].isin(part_filter))

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
# MONTHLY PERFORMANCE TREND (Bar Color Changed)
# =========================
st.markdown("---")
st.subheader("📈 Monthly Performance Trend")

if not filtered_df.empty:
    # Group by Month and Type
    monthly_trend = filtered_df.groupby(["Month", "Type"])["Value"].sum().reset_index()
    monthly_trend = monthly_trend.sort_values("Month")
    
    # Create the chart with NEW COLORS
    # Teal for Sales, Tomato for Returns
    fig_trend = px.bar(
        monthly_trend, 
        x="Month", 
        y="Value", 
        color="Type",
        barmode="group",
        labels={"Value": "Amount (OMR)", "Month": "Time Period"},
        color_discrete_map={
            "SALE": "#008080",    # Teal
            "RETURN": "#FF6347"   # Tomato/Red
        }
    )
    
    fig_trend.update_xaxes(dtick="M1", tickformat="%b %Y")
    fig_trend.update_layout(hovermode="x unified")
    
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.warning("No data found for the current filter selection.")

# =========================
# DISTRIBUTION CHARTS
# =========================
st.markdown("---")
c1, c2 = st.columns(2)
chart_data = filtered_df.copy()
chart_data["AbsValue"] = chart_data["Value"].abs()

if not chart_data.empty:
    fig_cat = px.pie(chart_data, values="AbsValue", names="Category", hole=0.5, 
                     title="Category Distribution", color_discrete_sequence=px.colors.qualitative.Safe)
    c1.plotly_chart(fig_cat, use_container_width=True)

    fig_ch = px.pie(chart_data, values="AbsValue", names="Channel", hole=0.5, 
                    title="Channel Distribution", color_discrete_sequence=px.colors.qualitative.Pastel)
    c2.plotly_chart(fig_ch, use_container_width=True)

# =========================
# FAST MOVING SKU (Top 10)
# =========================
st.markdown("---")
st.subheader("🔥 Top 10 Fast Moving SKU")
fast_sku = (
    filtered_df[filtered_df["Type"] == "SALE"]
    .groupby(["PartNo", "Category", "SubCategory"])["Qty"]
    .sum()
    .reset_index()
    .sort_values("Qty", ascending=False)
    .head(10)
)
st.dataframe(fast_sku, use_container_width=True)
