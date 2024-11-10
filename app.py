from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import io
import re
import webview
import threading
app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('debt_book.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/search_customers', methods=['GET'])
def search_customers():
    first_name_query = request.args.get('first_name', '').strip()
    last_name_query = request.args.get('last_name', '').strip()

    conn = get_db_connection()
    query = '''
        SELECT * FROM customers
        WHERE (? = '' OR first_name LIKE ?)
        AND (? = '' OR last_name LIKE ?)
    '''
    customers = conn.execute(query, (
        first_name_query, f'%{first_name_query}%',
        last_name_query, f'%{last_name_query}%'
    )).fetchall()
    conn.close()

    if not customers:
        return render_template('main.html', customers=[], error_message="Arama kriterlerine uygun müşteri bulunamadı.")

    return render_template('main.html', customers=customers)

@app.route('/print_customer/<int:customer_id>')
def print_customer(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    payments = conn.execute('SELECT * FROM payments WHERE customer_id = ?', (customer_id,)).fetchall()
    total_paid = sum(payment['amount'] for payment in payments)
    remaining_debt = customer['opening_balance'] - total_paid
    conn.close()

    return render_template('print.html', customer=customer, payments=payments,
                           total_paid=total_paid, remaining_debt=remaining_debt)


def clean_surname(last_name):
    """Function to clean last name and remove any text within parentheses."""
    pattern = r'\((.*?)\)'  # Regex to find text inside parentheses
    match = re.search(pattern, last_name)

    if match:
        return last_name.split('(')[0].strip()  # Get text before parentheses
    else:
        return last_name  # Return as is if no parentheses found

@app.template_filter('clean_surname')
def clean_surname_filter(last_name):
    return clean_surname(last_name)

@app.route('/')
def index():
    conn = get_db_connection()
    customers = conn.execute('SELECT * FROM customers ORDER BY registration_date DESC').fetchall()
    conn.close()
    return render_template('main.html', customers=customers)


@app.route('/show_image/<int:customer_id>')
def show_image(customer_id):
    conn = get_db_connection()
    customer = conn.execute('SELECT image FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()

    if customer and customer['image']:
        image_data = io.BytesIO(customer['image'])
        return send_file(image_data, mimetype='image/jpg')
    return 'Image not found', 404


@app.route('/add_customer', methods=('GET', 'POST'))
def add_customer():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        registration_date = request.form['registration_date']
        phone = request.form['phone']
        opening_balance = request.form['opening_balance']

        image = request.files.get('image')
        image_blob = None
        if image and image.filename:
            image_blob = image.read()

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO customers (first_name, last_name, registration_date, phone, image, opening_balance) VALUES (?, ?, ?, ?, ?, ?)',
            (first_name, last_name, registration_date, phone, image_blob, opening_balance))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add_customer.html')



@app.route('/credit_sales', methods=['GET', 'POST'])
def credit_sales():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
    else:
        first_name = request.args.get('first_name')
        last_name = request.args.get('last_name')

    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE first_name = ? AND last_name = ?', (first_name, last_name)).fetchone()

    if customer:
        payments = conn.execute('SELECT * FROM payments WHERE customer_id = ?', (customer['id'],)).fetchall()
        total_paid = sum(payment['amount'] for payment in payments)
        remaining_debt = customer['opening_balance'] - total_paid
        conn.close()
        return render_template('credit_sales.html', customer=customer, payments=payments,
                               total_paid=total_paid, remaining_debt=remaining_debt)

    conn.close()
    return redirect(url_for('index'))


@app.route('/add_payment', methods=['POST'])
def add_payment():
    first_name = request.form['creditSaleFirstName']
    last_name = request.form['creditSaleLastName']
    transaction_date_time = request.form['transactionDateTime']
    amount = float(request.form['amount'])
    payment_type = request.form['paymentType']
    description = request.form['description']

    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE first_name = ? AND last_name = ?', (first_name, last_name)).fetchone()

    if customer:
        conn.execute(
            'INSERT INTO payments (customer_id, amount, transaction_date_time, payment_type, description) VALUES (?, ?, ?, ?, ?)',
            (customer['id'], amount, transaction_date_time, payment_type, description))
        conn.commit()

    conn.close()
    return redirect(url_for('credit_sales', first_name=first_name, last_name=last_name))


@app.route('/update_tables', methods=['POST'])
def update_tables():
    first_name = request.form['creditSaleFirstName']
    last_name = request.form['creditSaleLastName']

    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE first_name = ? AND last_name = ?', (first_name, last_name)).fetchone()

    if customer:

        payments = conn.execute('SELECT * FROM payments WHERE customer_id = ?', (customer['id'],)).fetchall()
        conn.close()
        return render_template('credit_sales.html', customer=customer, payments=payments)

    return redirect(url_for('index'))



@app.route('/cash_book', methods=['GET'])
def cash_book():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    conn = get_db_connection()

    # Default date range if not provided
    if not start_date or not end_date:
        start_date = '0000-01-01'
        end_date = '9999-12-31'

    # Calculate total revenue
    total_revenue_query = '''
        SELECT SUM(opening_balance) AS total_revenue
        FROM customers
        WHERE registration_date BETWEEN ? AND ?
    '''

    total_revenue = conn.execute(total_revenue_query, (start_date, end_date)).fetchone()['total_revenue']

    # Calculate total cash sales
    total_cash_sales_query = '''
        SELECT SUM(amount) AS total_cash_sales
        FROM cash_sales
        WHERE transaction_date BETWEEN ? AND ?
    '''
    total_cash_sales = conn.execute(total_cash_sales_query, (start_date, end_date)).fetchone()['total_cash_sales']

    # Combine both revenues
    total_revenue = (total_revenue or 0) + (total_cash_sales or 0)

    # Calculate remaining debts
    remaining_debts_query = '''
        WITH TotalPayments AS (
            SELECT
                customer_id,
                SUM(amount) AS total_payments
            FROM payments
            GROUP BY customer_id
        )
        SELECT
            c.first_name,
            c.last_name,
            (c.opening_balance - COALESCE(tp.total_payments, 0)) AS remaining_debt
        FROM customers c
        LEFT JOIN TotalPayments tp ON c.id = tp.customer_id
        WHERE (c.opening_balance - COALESCE(tp.total_payments, 0)) > 0
        ORDER BY remaining_debt DESC
    '''
    remaining_debts = conn.execute(remaining_debts_query).fetchall()

    # Calculate total remaining debt
    total_remaining_debt = sum(row['remaining_debt'] for row in remaining_debts)

    conn.close()

    return render_template('cash_book.html',
                           remaining_credits_data=remaining_debts,
                           total_remaining_debt=total_remaining_debt,
                           total_revenue=total_revenue)

@app.route('/cash_sales', methods=['GET', 'POST'])
def cash_sales():
    if request.method == 'POST':
        transaction_date = request.form['transactionDate']
        product_type = request.form['productType']
        amount = float(request.form['amount'])
        payment_method = request.form['paymentMethod']

        conn = get_db_connection()
        conn.execute('INSERT INTO cash_sales (transaction_date, product_type, amount, payment_method) VALUES (?, ?, ?, ?)',
                     (transaction_date, product_type, amount, payment_method))
        conn.commit()
        conn.close()

        return redirect(url_for('cash_sales'))

    # Fetch the summary data for each product type
    conn = get_db_connection()
    summary_rows = conn.execute('''
        SELECT product_type, COUNT(*) AS total_quantity, SUM(amount) AS total_amount
        FROM cash_sales
        GROUP BY product_type
    ''').fetchall()
    conn.close()

    return render_template('cash_sales.html', summary_data=summary_rows)

# Running Flask in a separate thread
def run_flask():
    app.run(debug=True, use_reloader=False)  # Disable reloader to avoid issues with threading

if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start pywebview to display the app in a desktop window
    webview.create_window('Debt Book Application', 'http://127.0.0.1:5000/', width=1024, height=768)
    webview.start()