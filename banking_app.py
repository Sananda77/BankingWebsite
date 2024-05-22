import streamlit as st
import sqlite3
from datetime import datetime
from PIL import Image
import pandas as pd
import hashlib

# Load image
image = Image.open('image/logo.png')
image = image.resize((400, 400)) 

# Center-align image and text
col1, col2, col3 = st.columns([1, 3, 1])

# Display image
with col2:
    st.image(image, use_column_width=False) 

# Center-align text
with col2:
    st.markdown("<h2 style='text-align: center;'>UCB Banking Application</h2>", unsafe_allow_html=True)
    st.write("<p style='text-align: center; color: #0241c8;'>Made banking easy!</p>", unsafe_allow_html=True)

# Add a background image
st.markdown(
    """
    <style>
    body {
        background-image: url("image/logo.png");  /* Adjust the path */
        background-size: cover;
        background-position: center;
        font-family: 'sans-serif';  /* Set the font to a safe value */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Connect to SQLite database
conn = sqlite3.connect("bank.db")
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT
    )
""")

# Create accounts table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_number TEXT PRIMARY KEY,
        name TEXT,
        balance REAL
    )
""")

# Create transactions table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number TEXT,
        transaction_desc TEXT,
        amount REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (account_number) REFERENCES accounts(account_number)
    )
""")
conn.commit()

# Hashing function for passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validation function to check if a user exists
def user_exists(username):
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cursor.fetchone() is not None

# Validation function to check if an account exists
def account_exists(account_number):
    cursor.execute("SELECT * FROM accounts WHERE account_number = ?", (account_number,))
    return cursor.fetchone() is not None

# Define login function with validation
def login():
    st.title("Welcome to UCB Bank")
    username = st.text_input("Username", max_chars=20)
    password = st.text_input("Password", type="password", max_chars=20, key="password_input")

    if st.button("Login", key="login_button"):
        # Check if username exists
        if not user_exists(username):
            st.error("Username does not exist. Please try again or create a new user.")
            return

        # Fetch hashed password for the username
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        hashed_password = cursor.fetchone()[0]

        # Verify password
        if hashed_password != hash_password(password):
            st.error("Invalid password. Please try again.")
            return

        st.session_state.logged_in = True  # Set logged_in to True
        st.session_state.current_page = "Banking App"

# Define create user function with validation
def create_user():
    st.title("Create User")
    new_username = st.text_input("New Username", max_chars=20)
    new_password = st.text_input("New Password", type="password", max_chars=20)

    if st.button("Create User", key="create_user_button"):
        # Check if username already exists
        if user_exists(new_username):
            st.warning("Username already exists. Please choose a different one.")
            return

        # Create new user
        hashed_password = hash_password(new_password)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, hashed_password))
        conn.commit()
        st.success("User created successfully. You can now login.")

class InsufficientFundsError(Exception):
    pass

class Bank:
    @staticmethod
    def get_account(account_number):
        """
        Retrieves an account based on the provided account number.

        Args:
            account_number (str): The account number of the desired account.

        Returns:
            Account: The account object if found, None otherwise.
        """
        cursor.execute("SELECT * FROM accounts WHERE account_number = ?", (account_number,))
        account_data = cursor.fetchone()
        if account_data:
            account = Account(account_data[0])
            account.load_account_info()
            return account
        else:
            return None

    @staticmethod
    # Define create account function with validation
    def create_account(name, account_number, initial_balance=0):
        """
        Creates a new account and adds it to the bank's account database.

        Args:
            name (str): The name of the account holder.
            account_number (str): The unique account number.
            initial_balance (float): The initial balance of the account. Default is 0.
        """
        if account_exists(account_number):
            st.warning("Account already exists. Please choose a different account number.")
            return  # Return early if the account already exists

        cursor.execute("INSERT INTO accounts (account_number, name, balance) VALUES (?, ?, ?)", (account_number, name, initial_balance))
        conn.commit()
        if cursor.rowcount > 0:
            st.success("Account created successfully.")
        else:
            st.error("Failed to create account. Please try again.")

    @staticmethod
    def deposit(account_number, amount):
        """
        Deposits money into the specified account.

        Args:
            account_number (str): The account number of the target account.
            amount (float): The amount to be deposited.
        """
        account = Bank.get_account(account_number)
        if not account:
            st.error("Account does not exist. Please enter a valid account number.")
            return

        account.deposit(amount)
        account.add_transaction("Deposited", amount)

    @staticmethod
    def withdraw(account_number, amount):
        """
        Withdraws money from the specified account.

        Args:
            account_number (str): The account number of the target account.
            amount (float): The amount to be withdrawn.

        Raises:
            InsufficientFundsError: If withdrawal amount exceeds the available balance.
        """
        account = Bank.get_account(account_number)
        if not account:
            st.error("Account does not exist. Please enter a valid account number.")
            return

        try:
            account.withdraw(amount)
            account.add_transaction("Withdrawn", amount)  # Add withdrawal transaction
            st.success("Amount withdrawn successfully")
        except InsufficientFundsError as e:
            st.error(str(e))

    @staticmethod
    def balance_enquiry(account_number):
        account = Bank.get_account(account_number)
        if account:
            return account.balance_enquiry(), account._name
        else:
            st.warning("Account not found")

    @staticmethod
    def transaction_details(account_number):
        # Check if account exists
        if not account_exists(account_number):
            st.error("Account does not exist. Please enter a valid account number.")
            return

        # Fetch deposit transactions
        cursor.execute("SELECT transaction_desc AS action, amount, timestamp FROM transactions WHERE account_number = ? AND transaction_desc = 'Deposited' ORDER BY timestamp DESC", (account_number,))
        deposit_transactions = cursor.fetchall()

        # Fetch withdrawal transactions
        cursor.execute("SELECT transaction_desc AS action, amount, timestamp FROM transactions WHERE account_number = ? AND transaction_desc = 'Withdrawn' ORDER BY timestamp DESC", (account_number,))
        withdrawal_transactions = cursor.fetchall()

        # Combine deposit and withdrawal transactions
        transactions = deposit_transactions + withdrawal_transactions
        # Sort transactions by timestamp
        transactions.sort(key=lambda x: x[2], reverse=True)

        if transactions:
            return transactions
        else:
            st.warning("No transactions found for this account.")

class Account:
    def __init__(self, account_number):
        """
        Initializes the Account object with provided attributes.
        Args:
            account_number (str): Account number.
        """
        self._account_number = account_number
        self._name = ""
        self._balance = 0

    def load_account_info(self):
        """
        Load account information from the database.
        """
        cursor.execute("SELECT name, balance FROM accounts WHERE account_number = ?", (self._account_number,))
        account_data = cursor.fetchone()
        if account_data:
            self._name = account_data[0]
            self._balance = account_data[1]

    def deposit(self, amount):
        """
        Deposits money into the account and updates the balance.

        Args:
            amount (float): The amount to be deposited.
        """
        if amount > 0:
            self._balance += amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (self._balance, self._account_number))
            conn.commit()
        else:
            st.warning("Invalid deposit amount")

    def withdraw(self, amount):
        """
        Withdraws money from the account if sufficient funds are available.

        Args:
            amount (float): The amount to be withdrawn.

        Raises:
            InsufficientFundsError: If withdrawal amount exceeds the available balance.
        """
        if amount <= self._balance and amount > 0:
            self._balance -= amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (self._balance, self._account_number))
            conn.commit()
        else:
            raise InsufficientFundsError("Insufficient funds" if amount > 0 else "Invalid withdrawal amount")

    def balance_enquiry(self):
        """
        Retrieves the current balance

        Returns:
            float: The current balance.
        """
        return self._balance

    def add_transaction(self, transaction_desc, amount):
        """
        Adds a transaction to the account's transaction history.

        Args:
            transaction_desc (str): The description of the transaction.
            amount (float): The amount of the transaction.
        """
        cursor.execute("INSERT INTO transactions (account_number, transaction_desc, amount) VALUES (?, ?, ?)", (self._account_number, transaction_desc, amount))
        conn.commit()

    def get_transaction_history(self):
        """
        Retrieves the transaction history of the account.

        Returns:
            list: A list containing transaction details.
        """
        cursor.execute("SELECT transaction_desc, amount, timestamp FROM transactions WHERE account_number = ?", (self._account_number,))
        transactions = cursor.fetchall()
        return transactions

def banking_app():
    action = st.selectbox("Select Action", ("Create New Account", "Deposit Funds", "Withdraw Amount", "Balance Enquiry", "Transaction Details"))

    if action == "Create New Account":
        st.header("Create New Account")
        name = st.text_input("Enter your name:")
        account_number = st.text_input("Enter the account number:")
        initial_balance = st.number_input("Enter initial balance:", value=100)
        if st.button("Create Account", key="create_account_button"):
            Bank.create_account(name, account_number, initial_balance)
            # st.success("Account created successfully")

    elif action == "Deposit Funds":
        st.header("Deposit Funds")
        account_number = st.text_input("Enter the account number:")
        amount = st.number_input("Enter amount to deposit:", value=100)
        if st.button("Deposit", key="deposit_button"):
            Bank.deposit(account_number, amount)
            st.success("Funds Deposited successfully")

    elif action == "Withdraw Amount":
        st.header("Withdraw Amount")
        account_number = st.text_input("Enter the account number:")
        amount = st.number_input("Enter amount to withdraw:", value=50)
        if st.button("Withdraw", key="withdraw_button"):
            Bank.withdraw(account_number, amount)

    elif action == "Balance Enquiry":
        st.header(" Balance Enquiry")
        account_number = st.text_input("Enter the account number:")
        if st.button("Check Balance", key="balance_button"):
            balance_info = Bank.balance_enquiry(account_number)
            if balance_info:
                balance, name = balance_info
                st.success(f"Balance for {name}'s account: {balance}")

    elif action == "Transaction Details":
        st.header("Transaction Details")
        account_number = st.text_input("Enter the account number:")
        if st.button("View History", key="history_button"):
            transactions = Bank.transaction_details(account_number)
            if transactions:
                st.write("## Transaction History")
                df = pd.DataFrame(transactions, columns=["Action", "Amount", "Date/Time"])
                st.dataframe(df)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "Login"
if "password_entered" not in st.session_state:
    st.session_state.password_entered = None

if st.session_state.logged_in:
    if st.session_state.current_page == "Banking App":
        banking_app()
else:
    choice = st.radio("Choose an option", ("Login", "Create User"))
    if choice == "Login":
        login()
    elif choice == "Create User":
        create_user()