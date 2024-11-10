import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import mplcursors

# English month names
english_months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

# Establish SQLite connection
conn = sqlite3.connect('debt_book.db')

# Retrieve data from Customers, Payments, and Cash Sales tables
customers_df = pd.read_sql_query("SELECT registration_date, opening_balance FROM customers", conn)
payments_df = pd.read_sql_query("SELECT transaction_date_time, amount FROM payments", conn)
cash_sales_df = pd.read_sql_query("SELECT transaction_date, amount FROM cash_sales", conn)

# Convert date columns to datetime format
customers_df['registration_date'] = pd.to_datetime(customers_df['registration_date'], format='%Y-%m-%d')
payments_df['transaction_date_time'] = pd.to_datetime(payments_df['transaction_date_time'], format='%Y-%m-%d')
cash_sales_df['transaction_date'] = pd.to_datetime(cash_sales_df['transaction_date'], format='%Y-%m-%d')

# Add year and month columns
customers_df['year'] = customers_df['registration_date'].dt.year
customers_df['month'] = customers_df['registration_date'].dt.to_period('M')
payments_df['year'] = payments_df['transaction_date_time'].dt.year
payments_df['month'] = payments_df['transaction_date_time'].dt.to_period('M')
cash_sales_df['year'] = cash_sales_df['transaction_date'].dt.year
cash_sales_df['month'] = cash_sales_df['transaction_date'].dt.to_period('M')

# Filter data by year and create plots
unique_years = customers_df['year'].unique()

for year in unique_years:
    # Filter data for the specific year
    yearly_customers = customers_df[customers_df['year'] == year]
    yearly_payments = payments_df[payments_df['year'] == year]
    yearly_cash_sales = cash_sales_df[cash_sales_df['year'] == year]

    # Calculate monthly total work received
    monthly_work_total = yearly_customers.groupby('month')['opening_balance'].sum().reset_index()
    monthly_work_total = monthly_work_total.set_index('month').reindex(pd.period_range(start=f'{year}-01', end=f'{year}-12', freq='M')).reset_index()
    monthly_work_total.rename(columns={'index': 'month'}, inplace=True)

    # Calculate monthly payments
    monthly_revenue = yearly_payments.groupby('month')['amount'].sum().reset_index()
    monthly_revenue = monthly_revenue.set_index('month').reindex(pd.period_range(start=f'{year}-01', end=f'{year}-12', freq='M')).reset_index()
    monthly_revenue.rename(columns={'index': 'month'}, inplace=True)

    # Calculate monthly cash sales
    monthly_cash_sales = yearly_cash_sales.groupby('month')['amount'].sum().reset_index()
    monthly_cash_sales = monthly_cash_sales.set_index('month').reindex(pd.period_range(start=f'{year}-01', end=f'{year}-12', freq='M')).reset_index()
    monthly_cash_sales.rename(columns={'index': 'month'}, inplace=True)

    # Create plot
    plt.figure(figsize=(16, 8))

    # Style settings
    plt.style.use('ggplot')
    colors1 = plt.cm.Blues([0.6 + i * 0.05 for i in range(len(monthly_work_total))])
    colors2 = plt.cm.Greens([0.6 + i * 0.05 for i in range(len(monthly_revenue))])
    colors3 = plt.cm.Oranges([0.6 + i * 0.05 for i in range(len(monthly_cash_sales))])

    # Monthly work received plot
    plt.subplot(1, 2, 1)
    bars1 = plt.bar(monthly_work_total['month'].astype(str), monthly_work_total['opening_balance'], color=colors1)
    plt.title(f'{year} Monthly Work Received', fontsize=16, fontweight='bold')
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.xlabel('Month', fontsize=14)
    plt.ylabel('Total Work (EUR)', fontsize=14)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))

    # Add cursor (only to the left plot)
    cursor = mplcursors.cursor(bars1, hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text(
        f"Total work received in {english_months[monthly_work_total.iloc[sel.index]['month'].month - 1]} {monthly_work_total.iloc[sel.index]['month'].year}: {monthly_work_total.iloc[sel.index]['opening_balance']:,.0f} EUR"))

    # Monthly revenue plot
    plt.subplot(1, 2, 2)
    bars2 = plt.bar(monthly_revenue['month'].astype(str), monthly_revenue['amount'], color=colors2, label='Payments')
    bars3 = plt.bar(monthly_cash_sales['month'].astype(str), monthly_cash_sales['amount'], color=colors3, alpha=0.7, label='Cash Sales')

    monthly_total = pd.merge(monthly_revenue, monthly_cash_sales, on='month', how='outer', suffixes=('_payments', '_cash_sales'))
    monthly_total.fillna(0, inplace=True)
    monthly_total['total'] = monthly_total['amount_payments'] + monthly_total['amount_cash_sales']

    plt.title(f'{year} Monthly Total Revenue', fontsize=16, fontweight='bold')
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.xlabel('Month', fontsize=14)
    plt.ylabel('Total Revenue (EUR)', fontsize=14)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.legend()

    # Add cursor showing detailed information on total, payments, and cash sales
    cursor = mplcursors.cursor([bars2, bars3], hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text(
        f"Total in {english_months[monthly_total.iloc[sel.index]['month'].month - 1]} {monthly_total.iloc[sel.index]['month'].year}: {monthly_total.iloc[sel.index]['total']:,.0f} EUR\n"
        f"Payments: {monthly_total.iloc[sel.index]['amount_payments']:,.0f} EUR, Cash Sales: {monthly_total.iloc[sel.index]['amount_cash_sales']:,.0f} EUR"))

    plt.tight_layout()
    plt.show()

# Close the database connection
conn.close()
