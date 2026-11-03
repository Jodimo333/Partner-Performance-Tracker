import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect("mydata.db")
df = pd.read_sql_query("SELECT * FROM service_logs", conn)
conn.close()

# data cleaning
df['dealer_code'] = df['dealer_code'].fillna('UNKNOWN_DEALER')

# datetime format
df['start_date'] = pd.to_datetime(df['start_date'])
df['end_date'] = pd.to_datetime(df['end_date'])

# time of each intervention
df['duration_days'] = (df['end_date'] - df['start_date']).dt.days

# np.where -> if true: impose a penalty; if false: 0
penalty_doc = np.where(df['document_status'] != 'Complete', 10, 0)
penalty_sla = np.where(df['duration_days'] > 5, 20, 0)
penalty_fraud = np.where(df['duration_days'] < 0, 100, 0) # fraud = instant 0

# total penalty for each row
df['total_penalty'] = penalty_doc + penalty_sla + penalty_fraud

# we order by the dealer to analyze the general performance
dealer_stats = df.groupby('dealer_code').agg(
    total_tickets=('ticket_id', 'count'),
    sla_breaches=('duration_days', lambda x: (x > 5).sum()),
    frauds=('duration_days', lambda x: (x < 0).sum()),
    missing_docs=('document_status', lambda x: (x != 'Complete').sum()),
    avg_penalty=('total_penalty', 'mean') 
).reset_index()

# final risk score
dealer_stats['risk_score'] = 100 - dealer_stats['avg_penalty']
# we make sure the score doesn't go lower than 0
dealer_stats['risk_score'] = dealer_stats['risk_score'].clip(lower=0)

def assign_risk_tier(score):
    if score >= 85:
        return 'Low Risk (Green)'
    elif score >= 60:
        return 'Medium Risk (Yellow)'
    else:
        return 'High Risk (Red)'

dealer_stats['risk_tier'] = dealer_stats['risk_score'].apply(assign_risk_tier)

# dealers with the lowest scores
worst_dealers = dealer_stats.sort_values(by='risk_score', ascending=True).head(10)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(worst_dealers[['dealer_code', 'total_tickets', 'frauds', 'sla_breaches', 'risk_score', 'risk_tier']])
