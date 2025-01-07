from flask import Flask, render_template, redirect, request, url_for, flash, session
from flask_pymongo import PyMongo
import jwt
import datetime
from bson.objectid import ObjectId
from functools import wraps
from flask_session import Session


app = Flask(__name__)        
app.secret_key = 'my_secret_key'
app.config['MONGO_URI'] = "mongodb://localhost:27017/todo_database"
mongo = PyMongo(app)
collection = mongo.db.items
users_collection = mongo.db.users
app.config['SECRET_KEY'] = 'dhanvantari26'

# Session configuration
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Function to require token on protected routes
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('jwt_token')  # Fetch token from session
        print(token)

        if not token:
            error_message = 'Token is missing!'
            return render_template('error.html', error_message=error_message)

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'email': data['email']})
        except jwt.ExpiredSignatureError:
            error_message = 'Token has expired!'
            return render_template('error.html', error_message=error_message)
        except jwt.InvalidTokenError:
            error_message = 'Invalid Token!'
            return render_template('error.html', error_message=error_message)

        return f(current_user, *args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    return redirect(url_for('login'))  # Ensure login is the first step


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Getting form data
        email = request.form['email']
        password = request.form['password']
       
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Username already taken!', 'error')
            return redirect(url_for('signup'))

        # Insert the new user into MongoDB without hashing the password
        users_collection.insert_one({
            'email': email,
            'password': password  # Storing plain password (not recommended)
        })

        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))


    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email= request.form['email']
        password = request.form['password']

        # Check if user exists
        user = users_collection.find_one({'email': email})
        if user and user['password'] == password:  # Checking plain password
            # Generate JWT token
            token = jwt.encode({'email':email, 'exp': datetime.datetime.now() + datetime.timedelta(hours=1)},
                                app.config['SECRET_KEY'], algorithm='HS256')

            # Store token in session
            session['jwt_token'] = token

            flash('Login successful!', 'success')
            return redirect(url_for('home'))  # Redirect to /todo after login
        else:
            flash('Invalid username or password!', 'error')

    return render_template('login.html')


@app.route('/todo')
@token_required
def home(current_user):
    tasks = list(collection.find({'user':current_user["email"]}))
    return render_template("index.html", items=tasks)


@app.route("/add", methods=["POST", "GET"])
@token_required
def add(current_user):
    if request.method == "POST":
        task = {
            'task': request.form['item'],
            'user':current_user["email"]
        }
        collection.insert_one(task)
        flash('Task added successfully!', 'success')
        return redirect("/todo")  # Redirect to /todo after adding a task
@app.route("/del/<item_id>")
@token_required
def delete(current_user, item_id):
    collection.delete_one({'_id':ObjectId(item_id)})
    flash('Task deleted successfully!', 'success')
    return redirect("/todo")  # Redirect to /todo after deleting a task


@app.route('/edit/<item_id>', methods=['POST', 'GET'])
@token_required
def edit_task(current_user, item_id):
    if request.method == 'POST':
        new_name = request.form['new_name']
        collection.update_one(
            {'_id': ObjectId(item_id)},
            {'$set': {'task': new_name}}  # Update the task name
        )
        flash('Task updated successfully!', 'success')
        return redirect("/todo")  # Redirect after update


    existing_task = collection.find_one({'_id': ObjectId(item_id)})
    if not existing_task:
        flash('Task not found!', 'error')
        return redirect(url_for('home'))

    #return render_template("update.html", task=tasks, task_id=task_id, existing_task=existing_task)


@app.route('/logout')
@token_required
def logout(current_user):
    print(current_user)
    session.pop('jwt_token', None)  # Remove JWT from session
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))  # Redirect to login page after logout


if __name__ == "__main__":
    app.run(debug=True)
