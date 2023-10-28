from flask import Flask, render_template, request, redirect, url_for
import uuid
import datetime
import mysql.connector
import sys

app = Flask(__name__)

# Database configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="admin",
    database="users"
)
userName = "abc"
deliveryPersonnelName = "abc"

users = {}

# Create a cursor from the database connection
cursor = db.cursor()

@app.route('/')
def login():
    return render_template('login.html')


@app.route('/signup', methods=['POST'])
def signup_post():
    user_type = request.form['user-type-signup']
    full_name = request.form['full-name']
    email = request.form['email']
    contact_number = request.form['contact-number']
    address = request.form['address']
    username = request.form['new-username']
    password = request.form['new-password']
    if user_type == 'customer':
        # Insert into the 'customers' table
        cursor.execute("""
            INSERT INTO customers (full_name, email, contact_number, address, username, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (full_name, email, contact_number, address, username, password))
        db.commit()
    elif user_type == 'delivery_personnel':
        # Insert into the 'delivery_personnel' table
        cursor.execute("""
            INSERT INTO delivery_personnel (full_name, email, contact_number, username, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (full_name, email, contact_number, username, password))
        db.commit()

    return redirect(url_for('login'))

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    user_type = request.form['user-type-login']
    if user_type == 'customer':
        cursor.execute("""SELECT username FROM customers WHERE username = %s AND password = %s""", (username, password))
        user = cursor.fetchone()
        if user:
            return redirect(url_for('customer', username=username))
        else:
            return "Login Failed. Please try again."

    if user_type == 'delivery_personnel':
        # Insert into the 'customers' table
        cursor.execute("""SELECT username FROM delivery_personnel WHERE username = %s AND password = %s""", (username, password))
        user = cursor.fetchone()
        if user:
            return redirect(url_for('order', username=username))
        else:
            return "Login Failed. Please try again."

    cursor.close()
    return

@app.route('/order')
def order(): 
    username = request.args.get('username')
    global deliveryPersonnelName
    deliveryPersonnelName = username
    return render_template('delivery-personnel.html', username = username)

@app.route('/customer')
def customer(): 
    username = request.args.get('username')
    global userName
    userName = username
    return render_template('customer.html', username = username)


@app.route('/process_order', methods=['POST'])
def process_order():
    parcel_id = uuid.uuid4()
    order_id = str(parcel_id)
    pickup_address = request.form['pickup_address']
    drop_address = request.form['drop_address']
    quantity = request.form['quantity']
    weight = request.form['weight']
    if int(weight) <= 100:
       amount = 100
    else: 
        amount = weight
    cursor.execute("""select id from customers where username = %s""",(userName,))
    customer_id = cursor.fetchone()
    cursor.execute("""
            INSERT INTO parcel (id, pickup_address, drop_address, quantity, weight, amount, customer_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (order_id, pickup_address, drop_address, quantity, weight, amount, customer_id[0]))
    
    cursor.execute("""
            INSERT INTO shipping_details (date, status, parcel_id, customer_id)
            VALUES (%s, %s, %s, %s)
        """, (datetime.datetime.now(), "ORDERED", order_id, customer_id[0]))
    
    db.commit()
    return "Order processed successfully."

@app.route('/past_orders')
def past_orders(): 
    return render_template('past_orders.html', username = userName)



@app.route('/past', methods=['GET'])
def get_past():
    #to fetch from UI
    username = userName
    cursor.execute("""select id from customers where username = %s""",(username,))
    customer_id = cursor.fetchone()
    cursor.execute("""select * from shipping_details where customer_id = %s""", (customer_id[0],))
    parcels = cursor.fetchall()
    order_details = []
    for i in parcels:
        order = {}
        order['order_id'] = i[4]
        order['date'] = i[1]
        order['status'] = i[2]
        cursor.execute("""select delivery_personnel_id from parcel where id = %s""", (i[4],))
        delivery_personnel_id = cursor.fetchone()
        if delivery_personnel_id[0] is not None:
            cursor.execute("""select full_name, email, contact_number from delivery_personnel where id = %s""", (delivery_personnel_id[0],))
            deliver_personal_info = cursor.fetchone()
            order['delivery_personnel_full_name'] = deliver_personal_info[0]
            order['delivery_personnel_email'] = deliver_personal_info[1]
            order['delivery_personnel_contact_number'] = deliver_personal_info[2]
        order_details.append(order)
    return order_details


@app.route('/order_details', methods=['GET'])
def get_order():
    cursor.execute("""select parcel_id from shipping_details where status = 'ORDERED'""")
    parcel_id = cursor.fetchall()
    order_details = []
    for i in parcel_id:
        cursor.execute("SELECT * FROM parcel WHERE id = %s", (i[0],))
        results = cursor.fetchall()
        order = {}
        order['id'] = results[0][0]
        order['pickup_address'] = results[0][1]
        order['drop_address'] = results[0][2]
        order_details.append(order)
    return order_details

@app.route('/more_orders')
def more_orders(): 
    return render_template('order.html', username = userName)


@app.route('/change_status_confirm', methods=['GET'])
def change_status_to_confirm():
    status = "CONFIRMED"
    parcel_id = request.args.get('product_id')
    cursor.execute("SELECT id FROM delivery_personnel WHERE username = %s", (deliveryPersonnelName,))
    delivery_personnel_id = cursor.fetchall()
    cursor.execute("UPDATE parcel SET delivery_personnel_id = %s where id = %s",(delivery_personnel_id[0][0],parcel_id))
    db.commit()
    cursor.execute("""UPDATE shipping_details SET status = %s where parcel_id = %s""", (status, parcel_id))
    db.commit()
    return "Order status updated successfully"



@app.route('/orders_del', methods=['GET'])
def del_orders():
    cursor.execute("SELECT id FROM delivery_personnel WHERE username = %s", (deliveryPersonnelName,))
    delivery_personnel_id = cursor.fetchone()
    cursor.execute("SELECT * FROM parcel WHERE delivery_personnel_id = %s", (delivery_personnel_id[0],))
    parcels = cursor.fetchall()
    parcel_details = []
    for j in parcels:
        parcel = {}
        cursor.execute("""select status from shipping_details where parcel_id = %s""", (j[0],))
        status = cursor.fetchone()
        parcel['order_id'] = j[0]
        parcel['status'] = status[0]
        parcel['pickup_address'] = j[1]
        parcel['drop_address'] = j[2] 
        parcel['quantity'] = j[3]
        parcel['weight'] = j[4]
        parcel['amount'] = j[5]
        cursor.execute("""select full_name, email, contact_number from customers where id=%s""", (j[6],))
        customer_info = cursor.fetchone()
        parcel['customer_name'] = customer_info[0]
        parcel['customer_email'] = customer_info[1]
        parcel['customer_contact_no'] = customer_info[2]

        parcel_details.append(parcel)

    return parcel_details


@app.route('/change_status_pickup', methods=['GET'])
def change_status_pickup():
    parcel_id = request.args.get('product_id')
    status = "PICKUP"
    cursor.execute("""UPDATE shipping_details SET status = %s where parcel_id = %s""", (status, parcel_id))
    db.commit()
    return "Order status updated successfully"


@app.route('/change_status_delivered', methods=['GET'])
def change_status_deivered():
    parcel_id = request.args.get('product_id')
    status = "DELIVERED"
    query = "UPDATE shipping_details SET status = '{}' where parcel_id = '{}'".format(status, parcel_id)
    cursor.execute(query)
    db.commit()

    return "Order status updated successfully"




 
if __name__ == '__main__':
    app.run(debug=True)



