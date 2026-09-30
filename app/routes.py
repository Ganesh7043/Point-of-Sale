import csv
import io
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, session, redirect,
                   jsonify, Response)
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db, next_invoice_no, get_settings
from .auth import login_required, admin_required

bp = Blueprint('main', __name__)


# ---------- Auth ----------

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_role'] = user['role']
            return redirect('/admin' if user['role'] == 'admin' else '/billing')

        return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------- Pages ----------

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    return redirect('/admin' if session['user_role'] == 'admin' else '/billing')


@bp.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')


@bp.route('/billing')
@login_required
def billing():
    return render_template('billing.html')


# ---------- Product APIs (admin) ----------

@bp.route('/api/products', methods=['GET'])
@admin_required
def list_products():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY name").fetchall()
    db.close()
    return jsonify([dict(p) for p in products])


@bp.route('/api/products', methods=['POST'])
@admin_required
def create_product():
    data = request.get_json()
    if not data.get('name') or data.get('price', 0) < 0 or data.get('stock', 0) < 0:
        return jsonify({'error': 'Invalid product data'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (data['name'].strip(), float(data['price']), int(data['stock']))
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


@bp.route('/api/products/<int:pid>', methods=['PUT'])
@admin_required
def update_product(pid):
    data = request.get_json()
    if not data.get('name') or data.get('price', 0) < 0 or data.get('stock', 0) < 0:
        return jsonify({'error': 'Invalid product data'}), 400

    db = get_db()
    db.execute(
        "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
        (data['name'].strip(), float(data['price']), int(data['stock']), pid)
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


@bp.route('/api/products/<int:pid>', methods=['DELETE'])
@admin_required
def delete_product(pid):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (pid,))
    db.commit()
    db.close()
    return jsonify({'success': True})


# ---------- Customer APIs ----------

@bp.route('/api/customers', methods=['GET'])
@login_required
def list_customers():
    q = request.args.get('q', '').strip()
    db = get_db()
    if q:
        rows = db.execute(
            "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 30",
            (f'%{q}%', f'%{q}%')
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM customers ORDER BY name").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@bp.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO customers (name, phone) VALUES (?, ?)",
        (data['name'].strip(), data.get('phone', '').strip())
    )
    db.commit()
    cid = cur.lastrowid
    row = db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    db.close()
    return jsonify(dict(row))


@bp.route('/api/customers/<int:cid>', methods=['PUT'])
@admin_required
def update_customer(cid):
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    db = get_db()
    db.execute(
        "UPDATE customers SET name = ?, phone = ? WHERE id = ?",
        (data['name'].strip(), data.get('phone', '').strip(), cid)
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


@bp.route('/api/customers/<int:cid>', methods=['DELETE'])
@admin_required
def delete_customer(cid):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id = ?", (cid,))
    db.commit()
    db.close()
    return jsonify({'success': True})


# ---------- Staff APIs (admin) ----------

@bp.route('/api/staff', methods=['GET'])
@admin_required
def list_staff():
    db = get_db()
    rows = db.execute(
        "SELECT id, username, full_name, role FROM users ORDER BY role, full_name"
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@bp.route('/api/staff', methods=['POST'])
@admin_required
def create_staff():
    data = request.get_json()
    username = data.get('username', '').strip()
    if not username or not data.get('password') or not data.get('full_name'):
        return jsonify({'error': 'All fields are required'}), 400
    if data.get('role') not in ('admin', 'staff'):
        return jsonify({'error': 'Invalid role'}), 400

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        db.close()
        return jsonify({'error': 'Username already exists'}), 400

    db.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
        (username, generate_password_hash(data['password']),
         data['full_name'].strip(), data['role'])
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


@bp.route('/api/staff/<int:uid>', methods=['PUT'])
@admin_required
def update_staff(uid):
    data = request.get_json()
    if not data.get('full_name') or data.get('role') not in ('admin', 'staff'):
        return jsonify({'error': 'Invalid data'}), 400

    db = get_db()
    db.execute(
        "UPDATE users SET full_name = ?, role = ? WHERE id = ?",
        (data['full_name'].strip(), data['role'], uid)
    )
    if data.get('password'):
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(data['password']), uid)
        )
    db.commit()
    db.close()
    return jsonify({'success': True})


@bp.route('/api/staff/<int:uid>', methods=['DELETE'])
@admin_required
def delete_staff(uid):
    if uid == session['user_id']:
        return jsonify({'error': 'You cannot delete your own account'}), 400

    db = get_db()
    admins = db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
    target = db.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    if not target:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    if target['role'] == 'admin' and admins <= 1:
        db.close()
        return jsonify({'error': 'Cannot delete the last admin'}), 400

    db.execute("DELETE FROM users WHERE id = ?", (uid,))
    db.commit()
    db.close()
    return jsonify({'success': True})


# ---------- Sales APIs ----------

@bp.route('/api/sales')
@admin_required
def list_sales():
    db = get_db()
    sales = [dict(s) for s in db.execute('''
        SELECT t.*, COUNT(ti.id) AS item_count
        FROM transactions t
        LEFT JOIN transaction_items ti ON ti.transaction_id = t.id
        GROUP BY t.id
        ORDER BY t.id DESC
    ''').fetchall()]
    items = {}
    for row in db.execute("SELECT * FROM transaction_items"):
        items.setdefault(row['transaction_id'], []).append(dict(row))
    returns = {}
    for row in db.execute("SELECT * FROM returns"):
        returns.setdefault(row['transaction_id'], []).append(dict(row))
    db.close()
    for s in sales:
        s['items'] = items.get(s['id'], [])
        s['returns'] = returns.get(s['id'], [])
    return jsonify(sales)


@bp.route('/api/sales/<int:tid>')
@admin_required
def sale_detail(tid):
    db = get_db()
    t = db.execute("SELECT * FROM transactions WHERE id = ?", (tid,)).fetchone()
    if not t:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    items = [dict(i) for i in db.execute(
        "SELECT * FROM transaction_items WHERE transaction_id = ?", (tid,)
    ).fetchall()]
    returns = [dict(r) for r in db.execute(
        "SELECT * FROM returns WHERE transaction_id = ? ORDER BY id DESC", (tid,)
    ).fetchall()]
    db.close()

    sale = dict(t)
    sale['items'] = items
    sale['returns'] = returns
    return jsonify(sale)


# ---------- Returns / refunds ----------

@bp.route('/api/returns', methods=['POST'])
@admin_required
def create_return():
    data = request.get_json()
    tid = data.get('transaction_id')
    lines = data.get('items', [])
    if not tid or not lines:
        return jsonify({'error': 'Nothing to return'}), 400

    db = get_db()
    try:
        sale = db.execute("SELECT * FROM transactions WHERE id = ?", (tid,)).fetchone()
        if not sale:
            raise ValueError('Sale not found')

        refund_total = 0
        for line in lines:
            item = db.execute(
                "SELECT * FROM transaction_items WHERE id = ? AND transaction_id = ?",
                (line['item_id'], tid)
            ).fetchone()
            if not item:
                raise ValueError('Sale item not found')
            qty = int(line['quantity'])
            if qty < 1:
                raise ValueError('Invalid return quantity')
            if qty > item['quantity'] - (item['quantity_returned'] or 0):
                raise ValueError(f'Cannot return more than sold for {item["product_name"]}')
            refund_total += item['price'] * qty

        for line in lines:
            item = db.execute(
                "SELECT * FROM transaction_items WHERE id = ?", (line['item_id'],)
            ).fetchone()
            qty = int(line['quantity'])
            db.execute(
                "UPDATE transaction_items SET quantity_returned = quantity_returned + ? WHERE id = ?",
                (qty, line['item_id'])
            )
            if item['product_id']:
                db.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (qty, item['product_id'])
                )

        fully_returned = all(
            (i['quantity_returned'] or 0) >= i['quantity']
            for i in db.execute(
                "SELECT * FROM transaction_items WHERE transaction_id = ?", (tid,)
            ).fetchall()
        )
        db.execute(
            "UPDATE transactions SET status = ? WHERE id = ?",
            ('returned' if fully_returned else 'partially returned', tid)
        )
        db.execute(
            "INSERT INTO returns (transaction_id, staff_name, refund_total) VALUES (?, ?, ?)",
            (tid, session['user_name'], refund_total)
        )
        db.commit()
    except (ValueError, KeyError, TypeError) as e:
        db.close()
        return jsonify({'error': str(e)}), 400

    db.close()
    return jsonify({'success': True, 'refund_total': refund_total})


# ---------- Reports ----------

def _report_data(db, days):
    since = (datetime.now() - timedelta(days=days - 1)).strftime('%Y-%m-%d 00:00:00')
    sales = db.execute(
        '''SELECT date(created_at) AS day, COUNT(*) AS n, SUM(total) AS revenue
           FROM transactions
           WHERE created_at >= ? AND status != 'returned'
           GROUP BY date(created_at) ORDER BY day''',
        (since,)
    ).fetchall()
    top = db.execute(
        '''SELECT ti.product_name, SUM(ti.quantity) AS units, SUM(ti.quantity * ti.price) AS revenue
           FROM transaction_items ti
           JOIN transactions t ON t.id = ti.transaction_id
           WHERE t.created_at >= ? AND t.status != 'returned'
           GROUP BY ti.product_name ORDER BY units DESC LIMIT 10''',
        (since,)
    ).fetchall()
    returns_row = db.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(refund_total), 0) AS total FROM returns WHERE created_at >= ?",
        (since,)
    ).fetchone()
    revenue = sum(r['revenue'] or 0 for r in sales)
    count = sum(r['n'] for r in sales)
    return {
        'days': days,
        'sales': [dict(r) for r in sales],
        'top': [dict(r) for r in top],
        'revenue': revenue,
        'count': count,
        'avg_sale': revenue / count if count else 0,
        'returns_count': returns_row['n'],
        'returns_total': returns_row['total'],
    }


@bp.route('/api/reports')
@admin_required
def reports():
    days = min(int(request.args.get('days', 7)), 365)
    db = get_db()
    data = _report_data(db, days)
    db.close()
    return jsonify(data)


@bp.route('/api/reports/csv')
@admin_required
def reports_csv():
    days = min(int(request.args.get('days', 7)), 365)
    db = get_db()
    data = _report_data(db, days)
    settings = get_settings(db)
    db.close()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([f"{settings.get('shop_name', 'Simple POS')} — sales report, last {days} days"])
    w.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    w.writerow([])
    w.writerow(['Summary'])
    w.writerow(['Total sales', data['count']])
    w.writerow(['Revenue', f"{data['revenue']:.2f}"])
    w.writerow(['Average sale', f"{data['avg_sale']:.2f}"])
    w.writerow(['Returns', data['returns_count']])
    w.writerow(['Refunded', f"{data['returns_total']:.2f}"])
    w.writerow([])
    w.writerow(['Sales by day'])
    w.writerow(['Date', 'Sales', 'Revenue'])
    for s in data['sales']:
        w.writerow([s['day'], s['n'], f"{s['revenue']:.2f}"])
    w.writerow([])
    w.writerow(['Top products'])
    w.writerow(['Product', 'Units sold', 'Revenue'])
    for t in data['top']:
        w.writerow([t['product_name'], t['units'], f"{t['revenue']:.2f}"])

    filename = f"report_last_{days}_days.csv"
    return Response(
        buf.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


# ---------- Settings ----------

@bp.route('/api/settings', methods=['GET', 'PUT'])
@admin_required
def settings():
    db = get_db()
    if request.method == 'GET':
        data = get_settings(db)
        db.close()
        return jsonify(data)

    data = request.get_json()
    for key in ('shop_name', 'shop_address', 'shop_phone'):
        if key in data:
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(data[key]).strip())
            )
    db.commit()
    data = get_settings(db)
    db.close()
    return jsonify(data)


# ---------- Billing APIs ----------

@bp.route('/api/billing/products')
@login_required
def billing_products():
    q = request.args.get('q', '').strip()
    db = get_db()
    if q:
        rows = db.execute(
            "SELECT * FROM products WHERE name LIKE ? AND stock > 0 ORDER BY name LIMIT 50",
            (f'%{q}%',)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM products WHERE stock > 0 ORDER BY name LIMIT 50"
        ).fetchall()
    db.close()
    return jsonify([dict(p) for p in rows])


@bp.route('/api/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.get_json()
    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'Cart is empty'}), 400

    payment_method = data.get('payment_method', 'cash')
    paid_amount = float(data.get('paid_amount') or 0)
    customer_id = data.get('customer_id') or None

    db = get_db()
    try:
        # Resolve customer
        customer_name = ''
        if customer_id:
            cust = db.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()
            if not cust:
                raise ValueError('Customer not found')
            customer_name = cust['name']

        # Validate stock and compute total
        total = 0
        for item in items:
            product = db.execute(
                "SELECT * FROM products WHERE id = ?", (item['product_id'],)
            ).fetchone()
            if not product:
                raise ValueError('Product not found')
            qty = int(item['quantity'])
            if qty < 1 or qty > product['stock']:
                raise ValueError(f'Not enough stock for {product["name"]}')
            total += product['price'] * qty

        if payment_method == 'cash' and 0 < paid_amount < total:
            raise ValueError('Cash paid is less than the total')
        if paid_amount and paid_amount < total:
            paid_amount = total
        change_amount = max(0.0, paid_amount - total) if paid_amount else 0.0
        if not paid_amount:
            paid_amount = total

        invoice_no = next_invoice_no(db)
        db.execute(
            '''INSERT INTO transactions
               (invoice_no, customer_id, customer_name, staff_name, total,
                paid_amount, change_amount, payment_method, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')''',
            (invoice_no, customer_id, customer_name, session['user_name'],
             total, paid_amount, change_amount, payment_method)
        )
        txn_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Save items and reduce stock
        for item in items:
            product = db.execute(
                "SELECT * FROM products WHERE id = ?", (item['product_id'],)
            ).fetchone()
            qty = int(item['quantity'])
            db.execute(
                '''INSERT INTO transaction_items
                   (transaction_id, product_id, product_name, quantity, price)
                   VALUES (?, ?, ?, ?, ?)''',
                (txn_id, product['id'], product['name'], qty, product['price'])
            )
            db.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (qty, product['id'])
            )

        db.commit()
    except (ValueError, KeyError, TypeError) as e:
        db.close()
        return jsonify({'error': str(e)}), 400

    db.close()
    return jsonify({'success': True, 'invoice_no': invoice_no, 'total': total,
                    'change_amount': change_amount})
