from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


# API Gateway URL
PRODUCTS_API_URL = os.getenv('PRODUCTS_API_URL')
CART_API_URL = os.getenv('CART_API_URL')
ORDERS_API_URL = os.getenv('ORDERS_API_URL')
PAYMENTS_API_URL = os.getenv('PAYMENTS_API_URL')
USER_AUTH_API_URL = os.getenv('USER_AUTH_API_URL')


################################################################################
# Home
################################################################################
@app.route('/')
def index():
    return render_template('index.html')


################################################################################
# User Authentication
################################################################################
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        response = requests.post(f"{USER_AUTH_API_URL}/register", json={
            "action": "register",
            "Username": username,
            "Password": password,
            "Email": email
        })

        if response.status_code == 201:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Try again.', 'danger')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Send the login request to the User Authentication API
        response = requests.post(f"{USER_AUTH_API_URL}/login", json={
            "action": "login",
            "Username": username,
            "Password": password
        })

        # Process the login response
        if response.status_code == 200:
            data = response.json()
            session['user_name'] = username
            session['user_id'] = data['UserID']
            # session['role'] = data['Role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('products'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_name', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('products'))


################################################################################
# Products
################################################################################
@app.route('/products')
def products():
    response = requests.get(PRODUCTS_API_URL)
    
    if response.status_code == 200:
        products = response.json()
    else:
        products = []
    return render_template('products.html', products=products)

@app.route('/product/<product_id>')
def product_detail(product_id):
    # Call your Product API to get the details of a specific product
    response = requests.get(f"{PRODUCTS_API_URL}/{product_id}")

    # Check if the product was found
    if response.status_code == 200:
        product = response.json()
    else:
        product = None
    
    return render_template('product_detail.html', product=product)


################################################################################
# Carts
################################################################################
@app.route('/cart')
def cart():
    if 'user_name' not in session:
        flash('Please log in to view your cart.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # Fetch cart items for the user
    response = requests.get(f"{CART_API_URL}/{user_id}")
    
    if response.status_code == 200:
        cart_items = response.json()

        for item in cart_items:
            item['Price'] = float(item['Price'])  # Convert Price to float
            item['Quantity'] = int(item['Quantity'])  # Convert Quantity to int

        # Now calculate total price
        total_price = sum(item['Price'] * item['Quantity'] for item in cart_items)

    else:
        cart_items = []
        total_price = 0
        flash('Failed to load your cart.', 'danger')

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_name' not in session:
        flash('Please log in to add items to your cart.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_name = session['user_name']
    product_id = request.form['product_id']
    product_name = request.form['product_name']  
    image_url = request.form['image_url'] 
    quantity = request.form['quantity']
    price = request.form['price']
    merchant_id = request.form['merchant_id']
    merchant_name  = request.form['merchant_name']

    # Call the Cart API to add the item to the cart
    response = requests.post(f"{CART_API_URL}/{user_id}/add", json={
        "userId": user_id,
        "userName": user_name,
        "productId": product_id,
        "productName": product_name,
        "imageUrl": image_url,
        "quantity": quantity,
        "price": price,
        "merchantId": merchant_id,
        "merchantName": merchant_name
    })

    if response.status_code == 200:
        flash('Item added to cart!', 'success')
    else:
        flash('Failed to add item to cart.', 'danger')

    return redirect(url_for('products'))


@app.route('/cart/remove/<product_id>', methods=['GET'])
def remove_from_cart(product_id):
    if 'user_name' not in session:
        flash('Please log in to update your cart.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Call the Cart API to remove the item from the cart
    response = requests.delete(f"{CART_API_URL}/{user_id}/remove/{product_id}")

    if response.status_code == 200:
        flash('Item removed from cart.', 'success')
    else:
        flash('Failed to remove item from cart.', 'danger')

    return redirect(url_for('cart'))



@app.route('/cart/update', methods=['POST'])
def update_cart():
    if 'user_name' not in session:
        flash('Please log in to update your cart.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    source = request.form['source'] 

    # Get the quantities and product IDs from the form data
    quantities = request.form.getlist('quantities[]')
    product_ids = request.form.getlist('product_ids[]') 

    for i, product_id in enumerate(product_ids):
        quantity = int(quantities[i])

        # Call the Cart API to update the quantity for each product
        response = requests.put(f"{CART_API_URL}/{user_id}/update", json={
            "productId": product_id,
            "quantity": quantity
        })

        if response.status_code != 200:
            flash(f'Failed to update quantity for product {product_id}', 'danger')

    flash('Cart updated successfully!', 'success')
    
    if source == 'cart':
        return redirect(url_for('cart'))
    else:
        return redirect(url_for('checkout'))

# Cart item counter
@app.context_processor
def cart_item_count():
    cart_items_quantity = 0
    if 'user_id' in session:
        user_id = session['user_id']
        cart_response = requests.get(f"{CART_API_URL}/{user_id}")
        if cart_response.status_code == 200:
            cart_items = cart_response.json()
            # Sum up the quantity of each item in the cart (convert to int)
            cart_items_quantity = sum(int(item['Quantity']) for item in cart_items if 'Quantity' in item)
    
    # Return the value to be available in all templates
    return {'cart_items_quantity': cart_items_quantity}



################################################################################
# Checkout
################################################################################
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please log in to proceed with checkout.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch cart items from Cart API
    cart_response = requests.get(f"{CART_API_URL}/{user_id}")
    cart_items = cart_response.json() if cart_response.status_code == 200 else []

    # Fetch user information from the UserAuth API
    user_response = requests.get(f"{USER_AUTH_API_URL}/{user_id}")
    user_info = user_response.json() if user_response.status_code == 200 else {}

    for item in cart_items:
        item['Price'] = float(item['Price'])  # Convert Price to float
        item['Quantity'] = int(item['Quantity'])  # Convert Quantity to int

    # Now calculate total price
    total_price = sum(item['Price'] * item['Quantity'] for item in cart_items)


    if request.method == 'POST':
        order_id = request.form['order_id']
        amount = request.form['amount']
        
        # Check if 'Address' is in user_info, otherwise handle missing address
        shipping_address = user_info.get('Address', None)  # Safely get the Address field
        if not shipping_address:
            flash('Shipping address is required. Please update your profile.', 'danger')
            return redirect(url_for('checkout')) 
        
        # Validate if payment method is provided
        payment_method = request.form.get('payment_method', None)  # Safely get payment method
        if not payment_method:
            flash('Payment method is required. Please select a valid payment method.', 'danger')
            return redirect(url_for('checkout'))

        # Make Payment API call (not included in this code)
        payment_response = requests.post(f"{PAYMENTS_API_URL}/{user_id}", json={
            "orderId": order_id,
            "amount": amount,
            "paymentMethod": payment_method
        })

        # Prepare order data to send to the Orders API
        order_data = {
            "UserID": user_id,
            "Items": cart_items,
            "TotalPrice": total_price,
            "OrderStatus": "Shipped",
            "ShippingAddress": shipping_address, 
            "CartItems": cart_items
        }

        # Call the Orders API to create the order
        order_response = requests.post(f"{ORDERS_API_URL}/ecommerce/order", json=order_data)

        # Handle Payment and Order creation responses
        if payment_response.status_code == 201 and order_response.status_code == 201:
            flash('Payment and Order created successfully!', 'success')
            return redirect(url_for('orders'))
        else:
            flash('Payment or Order creation failed. Please try again.', 'danger')

    return render_template('checkout.html', cart_items=cart_items, total_price=total_price, user_info=user_info)



@app.route('/checkout/remove/<product_id>', methods=['GET'])
def remove_from_checkout(product_id):
    if 'user_name' not in session:
        flash('Please log in to update your cart.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Call the Cart API to remove the item from the cart
    response = requests.delete(f"{CART_API_URL}/{user_id}/remove/{product_id}")

    if response.status_code == 200:
        flash('Item removed from cart.', 'success')
    else:
        flash('Failed to remove item from cart.', 'danger')

    return redirect(url_for('checkout'))


################################################################################
# Orders
################################################################################
@app.route('/orders')
def orders():
    if 'user_name' not in session:
        flash('Please log in to view your orders.', 'danger')
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    
    # Call Orders API to get order history for the logged-in user
    response = requests.get(f"{ORDERS_API_URL}/ecommerce/order/{user_id}")

    if response.status_code == 200:
        orders = response.json() 
        
        for order in orders:
            for item in order.get('Items', []):
                item['Price'] = float(item['Price'])  # Convert price to float
                item['Quantity'] = int(item['Quantity'])  # Convert quantity to int
                
            # Remove fractional seconds from OrderDate and parse as datetime
            order['OrderDate'] = order['OrderDate'].split('.')[0]  # Remove fractional seconds
            order['OrderDate'] = datetime.strptime(order['OrderDate'], '%Y-%m-%d %H:%M:%S')
            
        # Sort items in the order by OrderDate (descending) 
        orders = sorted(orders, key=lambda x: x['OrderDate'], reverse=True)        
                
    else:
        flash('Failed to retrieve orders.', 'danger')
        orders = []

    return render_template('orders.html', orders=orders)


################################################################################
# Search
################################################################################
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()  # Get search query

    if not query:
        flash('Please enter a search query', 'warning')
        return redirect(url_for('products'))

    # Send the query to the API to filter results
    response = requests.get(f"{PRODUCTS_API_URL}?search={query}")

    if response.status_code == 200:
        products = response.json()  # Get filtered products from API
        
        if not products:
            flash('No products found matching your search.', 'warning')
    else:
        products = []
        flash('An error occurred while searching for products.', 'danger')

    return render_template('search_results.html', products=products, query=query)


################################################################################
# Account
################################################################################
@app.route('/account', methods=['GET', 'POST'])
def account():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your account.', 'danger')
        return redirect(url_for('login'))

    # GET request to fetch user info
    if request.method == 'GET':
        response = requests.get(f"{USER_AUTH_API_URL}/{user_id}")
        if response.status_code == 200:
            user_info = response.json()
        else:
            flash('Failed to retrieve user information.', 'danger')
            user_info = {}
        return render_template('account.html', user_info=user_info)

@app.route('/account/update', methods=['POST'])
def update_account():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to update your account.', 'danger')
        return redirect(url_for('login'))
    
    # Get updated user details from the form
    user_data = {
        'source': request.form['source'],
        'name': request.form['name'],
        'email': request.form['email'],
        'address': request.form['address'],
        'payment_method': request.form['payment_method']
    }

    # Make API request to update user info in the UserAuthAPI
    response = requests.patch(f"{USER_AUTH_API_URL}/{user_id}", json=user_data)

    if user_data['source'] == "account":
        if response.status_code == 200:
            flash('Account information updated successfully!', 'success')
        else:
            flash('Failed to update account information.', 'danger')

        return redirect(url_for('account'))

    else:
        if response.status_code == 200:
            flash('Billing information updated successfully!', 'success')
        else:
            flash('Failed to update Billing information.', 'danger')

        return redirect(url_for('checkout'))


if __name__ == '__main__':
    # app.run(debug=True)
    app.run(port=8000, debug=True)
