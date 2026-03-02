"""
 Advanced Analytics & Visualization Module
----------------------------------------------------------
Adds interactive charts, category breakdowns, and AI-based forecasting.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Import database connection from FINAL
from FINAL import get_business_db

# Optional Prophet import
try:
    from prophet import Prophet
    prophet_available = True
except ImportError:
    prophet_available = False

from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

# -----------------------------------------------------------------------------
# Forecasting Helper Functions
# -----------------------------------------------------------------------------
def prepare_time_series(user_id, business_id, value_type='sales', freq='M'):
    """
    Prepare time series data for forecasting.

    Parameters
    ----------
    user_id : int
    business_id : int
    value_type : str, 'sales' or 'profit'
    freq : str, 'D' (daily), 'W' (weekly), 'M' (monthly)

    Returns
    -------
    pd.DataFrame with columns ['ds', 'y'] (Prophet format) or empty if no data.
    """
    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT date, type, amount
            FROM transactions
            WHERE user_id = ? AND business_id = ?
            ORDER BY date
        """, conn, params=(user_id, business_id))

    if df.empty:
        return pd.DataFrame()

    df['date'] = pd.to_datetime(df['date'])

    if value_type == 'sales':
        ts = df[df['type'] == 'Sales'].groupby('date')['amount'].sum().reset_index()
    elif value_type == 'profit':
        sales = df[df['type'] == 'Sales'].groupby('date')['amount'].sum()
        expenses = df[df['type'] == 'Expense'].groupby('date')['amount'].sum()
        profit = (sales - expenses).fillna(0).reset_index()
        profit.columns = ['date', 'amount']
        ts = profit
    else:
        return pd.DataFrame()

    if ts.empty:
        return pd.DataFrame()

    ts = ts.set_index('date').resample(freq).sum().reset_index()
    ts.columns = ['ds', 'y']
    ts = ts.dropna()
    return ts

def forecast_with_prophet(df, periods=6, freq='M'):
    """
    Forecast using Facebook Prophet.
    """
    if not prophet_available:
        return None

    try:
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=(freq == 'W'),
            daily_seasonality=False,
            seasonality_mode='multiplicative'
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=periods, freq=freq)
        forecast = model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    except Exception as e:
        st.error(f"Prophet error: {str(e)}")
        return None

def forecast_with_linear_regression(df, periods=30, freq='D'):
    """
    Linear regression forecast. For monthly frequency, periods are in months.
    """
    try:
        df = df.copy()
        df['days'] = (df['ds'] - df['ds'].min()).dt.days
        X = df['days'].values.reshape(-1, 1)
        y = df['y'].values

        model = LinearRegression()
        model.fit(X, y)

        last_day = df['days'].max()
        if freq == 'M':
            # Approximate months as 30 days
            step = 30
        elif freq == 'W':
            step = 7
        else:  # 'D'
            step = 1
        future_days = np.arange(last_day + step, last_day + step * periods + step, step).reshape(-1, 1)
        pred = model.predict(future_days)

        future_dates = [df['ds'].min() + timedelta(days=int(d)) for d in future_days.flatten()]

        forecast = pd.DataFrame({
            'ds': future_dates,
            'yhat': pred,
            'yhat_lower': pred * 0.9,
            'yhat_upper': pred * 1.1
        })
        return forecast
    except Exception as e:
        st.error(f"Linear regression error: {str(e)}")
        return None

def get_forecast(user_id, business_id, target='sales', periods=30, freq='D', method='auto'):
    """
    Unified forecasting function.
    """
    ts = prepare_time_series(user_id, business_id, value_type=target, freq=freq)  # FIX: value_type instead of target
    if ts.empty or len(ts) < 3:
        return None

    if method == 'auto':
        method = 'prophet' if prophet_available else 'linear'

    if method == 'prophet' and prophet_available:
        return forecast_with_prophet(ts, periods, freq)
    else:
        return forecast_with_linear_regression(ts, periods, freq)

# -----------------------------------------------------------------------------
# Category Breakdown Functions
# -----------------------------------------------------------------------------
def get_expense_by_category(user_id, business_id, period=None):
    with get_business_db() as conn:
        query = """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND business_id = ? AND type = 'Expense'
        """
        params = [user_id, business_id]
        if period == 'week':
            query += " AND date >= date('now', '-7 days')"
        elif period == 'month':
            query += " AND date >= date('now', '-30 days')"
        elif period == 'year':
            query += " AND date >= date('now', '-1 year')"
        query += " GROUP BY category ORDER BY total DESC"
        df = pd.read_sql(query, conn, params=params)
    return df

def get_sales_by_category(user_id, business_id, period=None):
    with get_business_db() as conn:
        query = """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND business_id = ? AND type = 'Sales'
        """
        params = [user_id, business_id]
        if period == 'week':
            query += " AND date >= date('now', '-7 days')"
        elif period == 'month':
            query += " AND date >= date('now', '-30 days')"
        elif period == 'year':
            query += " AND date >= date('now', '-1 year')"
        query += " GROUP BY category ORDER BY total DESC"
        df = pd.read_sql(query, conn, params=params)
    return df

# -----------------------------------------------------------------------------
# Page Definitions
# -----------------------------------------------------------------------------
def sales_trends_page():
    st.title("Sales Trends")
    if not st.session_state.active_business_id:
        st.warning("Please select an active business first.")
        return

    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT date, amount
            FROM transactions
            WHERE user_id = ? AND business_id = ? AND type = 'Sales'
            ORDER BY date
        """, conn, params=(st.session_state.user_id, st.session_state.active_business_id))

    if df.empty:
        st.info("No sales data available.")
        return

    df['date'] = pd.to_datetime(df['date'])
    st.info(f"Total sales records: {len(df)} from {df['date'].min().date()} to {df['date'].max().date()}")

    period = st.radio("View", ["Daily", "Weekly", "Monthly"], horizontal=True)
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
    df_grouped = df.set_index('date').resample(freq_map[period]).sum().reset_index()

    fig = px.line(df_grouped, x='date', y='amount', title=f"Sales Trend ({period})", markers=True)
    fig.update_xaxes(tickformat='%b %d, %Y' if period=='Daily' else '%b %Y')
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", f"₹{df_grouped['amount'].sum():,.2f}")
    col2.metric("Average per period", f"₹{df_grouped['amount'].mean():,.2f}")
    col3.metric("Periods with data", len(df_grouped))

def profit_margins_page():
    st.title("Profit Margins Over Time")
    if not st.session_state.active_business_id:
        st.warning("Please select an active business first.")
        return

    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT date, type, amount
            FROM transactions
            WHERE user_id = ? AND business_id = ?
            ORDER BY date
        """, conn, params=(st.session_state.user_id, st.session_state.active_business_id))

    if df.empty:
        st.info("No transaction data.")
        return

    df['date'] = pd.to_datetime(df['date'])
    st.info(f"Total records: {len(df)} from {df['date'].min().date()} to {df['date'].max().date()}")

    pivot = df.pivot_table(index='date', columns='type', values='amount', aggfunc='sum').fillna(0)
    if 'Sales' not in pivot.columns:
        pivot['Sales'] = 0
    if 'Expense' not in pivot.columns:
        pivot['Expense'] = 0

    pivot['Profit'] = pivot['Sales'] - pivot['Expense']
    pivot['Margin'] = (pivot['Profit'] / pivot['Sales'] * 100).replace([np.inf, -np.inf], 0).fillna(0)

    period = st.radio("Resample", ["Daily", "Weekly", "Monthly"], horizontal=True)
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
    pivot_resampled = pivot.resample(freq_map[period]).sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Sales', x=pivot_resampled['date'], y=pivot_resampled['Sales']))
    fig.add_trace(go.Bar(name='Expenses', x=pivot_resampled['date'], y=pivot_resampled['Expense']))
    fig.add_trace(go.Scatter(name='Margin %', x=pivot_resampled['date'], y=pivot_resampled['Margin'],
                              yaxis='y2', line=dict(color='red', width=3)))
    fig.update_layout(
        title=f'Profit & Margin ({period})',
        yaxis=dict(title='Amount (₹)'),
        yaxis2=dict(title='Margin %', overlaying='y', side='right', range=[0, 100]),
        barmode='group'
    )
    fig.update_xaxes(tickformat='%b %d, %Y' if period=='Daily' else '%b %Y')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Profit", f"₹{pivot_resampled['Profit'].sum():,.2f}")
    col2.metric("Avg Margin", f"{pivot_resampled['Margin'].mean():.1f}%")
    col3.metric("Best Margin", f"{pivot_resampled['Margin'].max():.1f}%")

def expense_categories_page():
    st.title("Expense Category Breakdown")
    if not st.session_state.active_business_id:
        st.warning("Please select an active business first.")
        return

    period = st.selectbox("Period", ["All time", "Last 30 days", "Last 7 days", "This year"])
    period_map = {
        "All time": None,
        "Last 30 days": "month",
        "Last 7 days": "week",
        "This year": "year"
    }
    df_exp = get_expense_by_category(st.session_state.user_id, st.session_state.active_business_id,
                                     period_map[period])

    if df_exp.empty:
        st.info("No expense data.")
        return

    fig = px.pie(df_exp, values='total', names='category', title=f"Expense by Category ({period})")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Breakdown Table")
    df_exp['total'] = df_exp['total'].apply(lambda x: f"₹{x:,.2f}")
    st.dataframe(df_exp, use_container_width=True)

    st.divider()
    st.subheader("Sales by Category")
    df_sales = get_sales_by_category(st.session_state.user_id, st.session_state.active_business_id,
                                     period_map[period])
    if not df_sales.empty:
        fig2 = px.bar(df_sales, x='category', y='total', title=f"Sales by Category ({period})")
        st.plotly_chart(fig2, use_container_width=True)
        df_sales['total'] = df_sales['total'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_sales, use_container_width=True)
    else:
        st.info("No sales data.")

# -----------------------------------------------------------------------------
# Forecasting Page (Fully Functional)
# -----------------------------------------------------------------------------
def forecasting_page():
    st.title("AI-Based Forecasting")
    if not st.session_state.active_business_id:
        st.warning("Please select an active business first.")
        return

    st.markdown("""
    This page uses **Prophet** (or linear regression as fallback) to forecast future sales and profit.
    """)

    # ------------------------------------------------------------
    # Data summary and frequency analysis
    # ------------------------------------------------------------
    with get_business_db() as conn:
        sales_count = pd.read_sql("""
            SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
            FROM transactions
            WHERE user_id = ? AND business_id = ? AND type = 'Sales'
        """, conn, params=(st.session_state.user_id, st.session_state.active_business_id)).iloc[0]

        expense_count = pd.read_sql("""
            SELECT COUNT(*) as count
            FROM transactions
            WHERE user_id = ? AND business_id = ? AND type = 'Expense'
        """, conn, params=(st.session_state.user_id, st.session_state.active_business_id)).iloc[0]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sales Records", sales_count['count'])
        if sales_count['min_date']:
            st.caption(f"From: {sales_count['min_date']} to {sales_count['max_date']}")
            # Number of distinct days
            with get_business_db() as conn2:
                distinct_days = pd.read_sql("""
                    SELECT COUNT(DISTINCT date) as days
                    FROM transactions
                    WHERE user_id = ? AND business_id = ? AND type = 'Sales'
                """, conn2, params=(st.session_state.user_id, st.session_state.active_business_id)).iloc[0]['days']
            st.caption(f"Distinct days: {distinct_days}")
    with col2:
        st.metric("Expense Records", expense_count['count'])

    if sales_count['count'] == 0:
        st.warning("No sales data found. Please add some transactions first.")
        return

    # ------------------------------------------------------------
    # Pre‑compute data points for each frequency
    # ------------------------------------------------------------
    freq_options = [
        ("Daily", "D"),
        ("Weekly", "W"),
        ("Monthly", "M")
    ]

    freq_counts = {}
    for label, code in freq_options:
        ts = prepare_time_series(
            st.session_state.user_id,
            st.session_state.active_business_id,
            value_type='sales',  # FIX: use value_type, not target
            freq=code
        )
        freq_counts[label] = len(ts) if not ts.empty else 0

    st.subheader("Data availability by frequency")
    cols = st.columns(3)
    for i, (label, code) in enumerate(freq_options):
        with cols[i]:
            count = freq_counts[label]
            if count >= 3:
                st.success(f"**{label}**: {count} points ✓")
            else:
                st.error(f"**{label}**: {count} points ✗ (need ≥3)")

    # ------------------------------------------------------------
    # User selections
    # ------------------------------------------------------------
    target = st.radio("Forecast", ["Sales", "Profit"], horizontal=True)
    freq_option = st.selectbox("Data frequency", ["Daily", "Weekly", "Monthly"], index=2)  # default Monthly
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[freq_option]

    if freq == 'D':
        periods = st.slider("Forecast horizon (days)", 7, 90, 30)
        unit = "days"
    elif freq == 'W':
        periods = st.slider("Forecast horizon (weeks)", 1, 12, 4)
        unit = "weeks"
    else:  # 'M'
        periods = st.slider("Forecast horizon (months)", 1, 12, 6)
        unit = "months"

    # ------------------------------------------------------------
    # Check if selected frequency has enough data
    # ------------------------------------------------------------
    enough = freq_counts[freq_option] >= 3
    if not enough:
        st.error(f"❌ Not enough data at {freq_option} frequency (only {freq_counts[freq_option]} point(s)).")
        # Suggest viable frequencies
        viable = [label for label, cnt in freq_counts.items() if cnt >= 3]
        if viable:
            st.info(f"✅ Frequencies with enough data: {', '.join(viable)}. Try one of those.")
        else:
            # No frequency has enough data – explain why and what to do
            st.warning("⚠️ No frequency currently has 3 or more data points.")
            if distinct_days == 1:
                st.error("All your sales transactions are on the **same day**. Forecasting requires data spread over multiple days/weeks/months.")
                st.info("💡 Please add transactions on different dates. Even a few days apart will help.")
            else:
                st.info("💡 You need more transactions spread over time. The more varied the dates, the better.")
        # Disable the generate button
        st.button("Generate Forecast", disabled=True)
        return

    # ------------------------------------------------------------
    # Proceed with forecast
    # ------------------------------------------------------------
    if st.button("Generate Forecast", type="primary"):
        with st.spinner("Calculating forecast..."):
            forecast = get_forecast(
                st.session_state.user_id,
                st.session_state.active_business_id,
                target=target.lower(),
                periods=periods,
                freq=freq
            )

        if forecast is None or forecast.empty:
            st.error("Forecasting failed unexpectedly.")
            return

        # Get historical data
        hist = prepare_time_series(st.session_state.user_id, st.session_state.active_business_id,
                                   value_type=target.lower(), freq=freq)  # FIX: use value_type
        hist = hist[hist['y'] > 0]  # remove zero entries for cleaner chart

        # Create plot
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=hist['ds'], y=hist['y'],
            mode='lines+markers',
            name='Historical',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ))

        fig.add_trace(go.Scatter(
            x=forecast['ds'], y=forecast['yhat'],
            mode='lines+markers',
            name='Forecast',
            line=dict(color='orange', width=2, dash='dash'),
            marker=dict(size=6)
        ))

        fig.add_trace(go.Scatter(
            x=forecast['ds'], y=forecast['yhat_upper'],
            mode='lines',
            line=dict(width=0),
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=forecast['ds'], y=forecast['yhat_lower'],
            mode='lines',
            fill='tonexty',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(width=0),
            name='Confidence Interval'
        ))

        # Format x-axis based on frequency
        if freq == 'D':
            tickformat = '%b %d'
        elif freq == 'W':
            tickformat = '%b %d, %Y'
        else:  # 'M'
            tickformat = '%b %Y'

        fig.update_layout(
            title=f"{target} Forecast ({freq_option})",
            xaxis_title="Date",
            yaxis_title="Amount (₹)",
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            xaxis=dict(tickformat=tickformat)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Next period prediction
        if not forecast.empty:
            next_val = forecast.iloc[0]['yhat']
            st.metric(f"Next {unit.capitalize()} Prediction", f"₹{next_val:,.2f}")

        # Show forecast table
        with st.expander("View Forecast Values"):
            display = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            if freq == 'D':
                display['ds'] = display['ds'].dt.strftime('%Y-%m-%d')
            elif freq == 'W':
                display['ds'] = display['ds'].dt.strftime('%Y-%m-%d')
            else:
                display['ds'] = display['ds'].dt.strftime('%Y-%m')
            display['yhat'] = display['yhat'].apply(lambda x: f"₹{x:,.2f}")
            display['yhat_lower'] = display['yhat_lower'].apply(lambda x: f"₹{x:,.2f}")
            display['yhat_upper'] = display['yhat_upper'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display, use_container_width=True)