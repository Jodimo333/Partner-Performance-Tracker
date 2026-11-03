import sqlite3
import numpy as np
from datetime import datetime, timedelta
import random

conn = sqlite3.connect("mydata.db")
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS service_logs')
cursor.execute('''
    CREATE TABLE service_logs (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dealer_code TEXT,
        asset_type TEXT,
        start_date TEXT,
        end_date TEXT,
        document_status TEXT
    )
''')

# 100 dealers
dealers = [f"DLR-{str(i).zfill(3)}" for i in range(1, 101)]

# asymmetry + chaos for pareto
# some dealers might be very active and problematic, whereas some barely visible
pareto_weights = np.random.pareto(a=1.16, size=100)
pareto_weights /= pareto_weights.sum()  

num_records = 20000

# asymmetric probabilities
chosen_dealers = np.random.choice(dealers, size=num_records, p=pareto_weights)

records = []
base_date = datetime(2025, 1, 1)

for dealer in chosen_dealers:
    asset = random.choice(['Replacement Vehicle', 'Diagnostic Tool', 'Transport Van'])
    start_date = base_date + timedelta(days=random.randint(0, 365))
    
    # risk / noise
    risk_roll = random.random()
    
    if risk_roll < 0.05:
        # 5% -> fraud / cronological error
        end_date = start_date - timedelta(days=random.randint(1, 5))
        doc_status = 'Missing' if random.random() < 0.5 else 'Complete'
        
    elif risk_roll < 0.25:
        # 20% -> massive SLA load
        end_date = start_date + timedelta(days=random.randint(15, 40))
        doc_status = random.choice(['Missing', 'Incomplete', 'Complete'])
        
    else:
        # 75% -> normal behavior
        end_date = start_date + timedelta(days=random.randint(1, 5))
        doc_status = 'Complete'
        
    # in approx 3% of tickets, we completely lose the code of the dealer
    final_dealer = None if random.random() < 0.03 else dealer
    
    records.append((
        final_dealer, 
        asset, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"), 
        doc_status
    ))

cursor.executemany('''
    INSERT INTO service_logs (dealer_code, asset_type, start_date, end_date, document_status)
    VALUES (?, ?, ?, ?, ?)
''', records)

conn.commit()
conn.close()
