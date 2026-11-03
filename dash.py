import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Partner Performance Tracker", layout="wide")
st.title("Partner Performance Tracker")
st.markdown("Keeping an eye on repair delays, missing documents, and data anomalies.")

# audit and extraction function
# @st.cache_data to load instantly
@st.cache_data
def run_audit():
    # extraction
    conn = sqlite3.connect("mydata.db")
    df = pd.read_sql_query("SELECT * FROM service_logs", conn)
    conn.close()

    # data cleaning
    df['dealer_code'] = df['dealer_code'].fillna('UNKNOWN')
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    df['duration_days'] = (df['end_date'] - df['start_date']).dt.days

    # risk score
    penalty_doc = np.where(df['document_status'] != 'Complete', 10, 0)
    penalty_sla = np.where(df['duration_days'] > 5, 20, 0)
    penalty_fraud = np.where(df['duration_days'] < 0, 100, 0)
    df['total_penalty'] = penalty_doc + penalty_sla + penalty_fraud

    dealer_stats = df.groupby('dealer_code').agg(
        total_tickets=('ticket_id', 'count'),
        sla_breaches=('duration_days', lambda x: (x > 5).sum()),
        frauds=('duration_days', lambda x: (x < 0).sum()),
        missing_docs=('document_status', lambda x: (x != 'Complete').sum()),
        avg_penalty=('total_penalty', 'mean')
    ).reset_index()

    dealer_stats['risk_score'] = 100 - dealer_stats['avg_penalty']
    dealer_stats['risk_score'] = dealer_stats['risk_score'].clip(lower=0)

    def assign_risk_tier(score):
        if score >= 85:
            return '🟢Low Risk'
        elif score >= 60:
            return '🟡Medium Risk'
        else:
            return '🔴High Risk'

    dealer_stats['risk_tier'] = dealer_stats['risk_score'].apply(assign_risk_tier)
    return dealer_stats

risk_df = run_audit()

# interface (KPIs)
st.markdown("### KPIs")
col1, col2, col3 = st.columns(3)

high_risk_count = len(risk_df[risk_df['risk_tier'] == '🔴High Risk'])
total_frauds = risk_df['frauds'].sum()

# metric cards
col1.metric("Audited partners", len(risk_df))
col2.metric("Red Flag Dealers", high_risk_count)
col3.metric("Total Frauds", total_frauds)

st.markdown("---")

# top 10 plotly
st.markdown("### Top 10 Problematic Partners")
worst_dealers = risk_df.sort_values(by='risk_score', ascending=True).head(10)

# bar chart
fig = px.bar(
    worst_dealers, 
    x='dealer_code', 
    y='risk_score',
    color='risk_score',
    color_continuous_scale='Reds_r', 
    text_auto='.2f',
    labels={'dealer_code': 'Partner Code', 'risk_score': 'Risk Score (100 = Flawless)'}
)
fig.update_layout(xaxis_title="", yaxis_title="Trust Score")
st.plotly_chart(fig, use_container_width=True)

# table
st.markdown("### Complete Audit Report")
st.dataframe(risk_df.sort_values(by='risk_score', ascending=True), use_container_width=True, hide_index=True)
