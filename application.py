import os
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from jinja2 import Template
from helper import login_required

import Queries as q

app = Flask(__name__)

app.config["DEBUG"] = True

db = q.create_connection("app_database.db")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./flask_session_cache"
Session(app)


@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    if request.method == 'POST':
        new_reason = request.form.get("reason")
        new_amount = float(request.form.get("amount"))
        
        # Fetch the old amount of the transaction being edited
        old_transaction_query = "SELECT amount FROM transactions WHERE id = :transaction_id"
        old_transaction_variables = {"transaction_id": transaction_id}
        old_transaction = q.sql_select_query(db, old_transaction_query, old_transaction_variables)
        
        if old_transaction:
            old_amount = old_transaction[0]["amount"]
            
            # Update the transaction in the database
            sql_query = "UPDATE transactions SET reason = :reason, amount = :amount WHERE id = :transaction_id"
            variables = {"reason": new_reason, "amount": new_amount, "transaction_id": transaction_id}
            q.sql_insert_query(db, sql_query, variables)
            
            # Fetch the current user's balance
            user_id = session["user_id"]
            user_balance_query = "SELECT balance FROM users WHERE id = :user_id"
            user_balance_variables = {"user_id": user_id}
            user_balance = q.sql_select_query(db, user_balance_query, user_balance_variables)
            
            if user_balance:
                current_balance = user_balance[0]["balance"]
                
                # Calculate the difference between the old amount and the new amount
                difference = new_amount - old_amount
                
                # Update the user's balance in the database
                new_balance = current_balance + difference
                update_balance_query = "UPDATE users SET balance = :new_balance WHERE id = :user_id"
                update_balance_variables = {"new_balance": new_balance, "user_id": user_id}
                q.sql_insert_query(db, update_balance_query, update_balance_variables)
                
                # Redirect to the statement page after editing
                return redirect("/statement")
        
        # Transaction not found or user balance not found, handle accordingly
        flash("Transaction not found or user balance not found", "error")
        return redirect("/statement")

    else:
        # Fetch the transaction details from the database based on transaction_id
        sql_query = "SELECT * FROM transactions WHERE id = :transaction_id"
        variables = {"transaction_id": transaction_id}
        transaction = q.sql_select_query(db, sql_query, variables)
        
        if transaction:
            pre_existing_reasons = ["Income", "Groceries", "Utilities", "Rent", "Entertainment", "Transportation", "Food"]
            return render_template("edit_transaction.html", transaction=transaction[0], reasons=pre_existing_reasons)
        else:
            # Transaction not found, handle accordingly
            flash("Transaction not found", "error")
            return redirect("/statement")


@app.route('/delete_transaction/<int:transaction_id>', methods=['GET'])
@login_required
def delete_transaction(transaction_id):
    # Fetch the amount of the transaction being deleted
    sql_query = "SELECT amount FROM transactions WHERE id = :transaction_id"
    variables = {"transaction_id": transaction_id}
    deleted_transaction = q.sql_select_query(db, sql_query, variables)

    if deleted_transaction:
        deleted_amount = deleted_transaction[0]["amount"]

        # Fetch the current total balance
        user_id = session["user_id"]
        sql_query = "SELECT balance FROM users WHERE id = :user_id"
        variables = {"user_id": user_id}
        current_balance = q.sql_select_query(db, sql_query, variables)

        if current_balance:
            current_balance = current_balance[0]["balance"]
            # Calculate the new total balance after deleting the transaction
            new_balance = current_balance + deleted_amount  # Subtracting the deleted amount

            # Update the user's balance in the database
            sql_query = "UPDATE users SET balance = :new_balance WHERE id = :user_id"
            variables = {"new_balance": new_balance, "user_id": user_id}
            q.sql_insert_query(db, sql_query, variables)

        # Delete the transaction from the database based on transaction_id
        sql_query = "DELETE FROM transactions WHERE id = :transaction_id"
        variables = {"transaction_id": transaction_id}
        q.sql_insert_query(db, sql_query, variables)

    # Redirect to the statement page after deletion
    return redirect("/statement")



@app.route('/', methods = ['GET'])
def index():
	return render_template("index.html")


@app.route('/credit', methods=['GET', 'POST'])
def credit():
    if request.method == 'POST':
        user_id = session["user_id"]
        amount = float(request.form.get("amount"))
        reason = request.form.get("reason")
        
        if reason == "custom":
            reason = request.form.get("customReason")

        # Insert the transaction into the database
        type_of_transaction = "C"
        sql_query = "INSERT INTO transactions(user_id, reason, type, amount) VALUES (:user_id, :reason, :type, :amount)"
        variable = dict(user_id=session["user_id"], reason=reason, type=type_of_transaction, amount=amount)
        q.sql_insert_query(db, sql_query, variable)
        
        # Fetch the current balance after the transaction is inserted
        users_balance = "SELECT balance FROM users WHERE id = :user_id"
        rows = q.sql_select_query(db, users_balance, dict(user_id=user_id))
        balance = rows[0][0]  # Fetching the current balance from the database
        
        # Update the balance with the added amount
        balance += amount
        
        # Update the user's balance in the database
        sql_query = "UPDATE users SET balance = :balance WHERE id = :user_id"
        variable = dict(balance=balance, user_id=user_id)
        q.sql_insert_query(db, sql_query, variable)
        
    return redirect("/transaction")



@app.route('/debit', methods=['GET', 'POST'])
def debit():
    if request.method == 'POST':
        user_id = session["user_id"]
        amount = float(request.form.get("amount"))
        reason = request.form.get("reason")
        
        if reason == "custom":
            reason = request.form.get("customReason")

        # Insert the transaction into the database
        type_of_transaction = "D"
        sql_query = "INSERT INTO transactions(user_id, reason, type, amount) VALUES (:user_id, :reason, :type, :amount)"
        variable = dict(user_id=session["user_id"], reason=reason, type=type_of_transaction, amount=amount)
        q.sql_insert_query(db, sql_query, variable)
        
        # Fetch the current balance after the transaction is inserted
        users_balance = "SELECT balance FROM users WHERE id = :user_id"
        rows = q.sql_select_query(db, users_balance, dict(user_id=user_id))
        balance = rows[0][0]  # Fetching the current balance from the database
        
        # Update the balance with the subtracted amount
        balance -= amount
        
        # Update the user's balance in the database
        sql_query = "UPDATE users SET balance = :balance WHERE id = :user_id"
        variable = dict(balance=balance, user_id=user_id)
        q.sql_insert_query(db, sql_query, variable)
        
    return redirect("/transaction")


@app.route('/login', methods = ['GET','POST'])
def login():
	if request.method == 'POST':
		username = request.form.get("username")
		pd = request.form.get("password")
		sql_query = "SELECT * from users where uname = :username"
		rows = q.sql_select_query(db,sql_query, dict(username = username))
		if(len(rows) < 1):
			flash("Username does not exists",'error')
		else:
			user_password = rows[0]["password"]
			print(user_password)
			print(generate_password_hash(pd))
			if(not check_password_hash(user_password,pd)) :
				flash("Incorrect Password",'error')
			else:
				session["user_id"] = rows[0]["id"]
				return redirect("/")
	return render_template("login.html", show_forms=True)


@app.route('/logout',methods = ['GET','POST'])
@login_required
def logout():
	session.clear()
	return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if the username already exists in the database
        username = request.form.get("username")
        existing_user_query = "SELECT id FROM users WHERE uname = :username"
        existing_user = q.sql_select_query(db, existing_user_query, {"username": username})
        
        # If the username already exists, show an error message
        if existing_user:
            flash("Username already exists. Please choose a different username.")
            return render_template("register.html", show_forms=True)
        
        # Check if the password matches the confirmed password
        if request.form.get("password") != request.form.get("confirmPassword"):
            flash("Passwords do not match. Please try again.")
            return render_template("register.html", show_forms=True)

        # Set initial balance to 0 for new user
        initial_balance = 0

        # Insert new user into the database with initial balance
        sql_query = "INSERT INTO users (uname, password, balance) VALUES (:username, :password, :balance)"
        q.sql_insert_query(db, sql_query, {"username": username, "password": generate_password_hash(request.form.get("password")), "balance": initial_balance})
        
        return redirect("/")
    
    else:
        return render_template("register.html", show_forms=True)


@app.route('/statement', methods=['GET'])
@login_required
def statement():
    user_id = session["user_id"]

    # Fetch all transactions for the user
    sql_query = "SELECT * FROM transactions WHERE user_id = :user_id"
    variables = {"user_id": user_id}
    rows = q.sql_select_query(db, sql_query, variables)

    # Fetch the user's initial balance
    sql_query = "SELECT balance FROM users WHERE id = :user_id"
    variables = {"user_id": user_id}
    balance_row = q.sql_select_query(db, sql_query, variables)

    # Initialize balance with the initial balance of the user
    # if balance_row:
    #     balance = balance_row[0]["balance"]
    # else:
    balance = 0

    # Adjust balance based on each transaction
    for record in rows:
        if record["type"] == "C":
            balance += record["amount"]
        elif record["type"] == "D":
            balance -= record["amount"]

    return render_template("statement.html", records=rows, balance=balance)



@app.route('/transaction',methods = ['GET','POST'])
@login_required
def transaction():
	pre_existing_reasons = ["Income", "Groceries", "Utilities", "Rent", "Entertainment", "Transportation", "Food"]

	return render_template("transaction.html",  reasons=pre_existing_reasons)

if __name__ == '__main__':
	app.run()
	#bitch