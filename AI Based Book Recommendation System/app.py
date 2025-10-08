from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-this-secret-for-prod")

# MongoDB setup - set MONGO_URI in env or edit below for local testing
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client.book_recommender
users_col = db.users

# Example data - in real app you'd have a books collection
BOOKS = [
    {"id": 1, "title": "Clean Code", "author": "Robert C. Martin", "price": 299},
    {"id": 2, "title": "Atomic Habits", "author": "James Clear", "price": 249},
    {"id": 3, "title": "Deep Work", "author": "Cal Newport", "price": 199},
]

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return users_col.find_one({"_id": uid})

@app.route("/")
def home():
    user = current_user()
    return render_template("home.html", books=BOOKS, user=user)

@app.route("/about")
def about():
    user = current_user()
    return render_template("base.html", page_title="About", user=user, content_title="About",
                           content="<p>This is a simple AI-powered book recommender starter app.</p>")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    user = current_user()
    if request.method == "POST":
        # For now just flash the message; later you can store it in DB or send email
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        flash("Thanks for contacting us, we'll get back to you.", "success")
        return redirect(url_for("contact"))
    contact_html = """
    <form method="post" class="card small-card">
      <label>Name<input name="name" required></label>
      <label>Email<input name="email" type="email" required></label>
      <label>Message<textarea name="message" rows="4" required></textarea></label>
      <button type="submit" class="btn">Send</button>
    </form>
    """
    return render_template("base.html", page_title="Contact", user=user, content_title="Contact", content=contact_html)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = request.get_json() or request.form
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not name or not email or not password:
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if users_col.find_one({"email": email}):
            return jsonify({"success": False, "message": "Email already registered."}), 400

        hashed = generate_password_hash(password)
        inserted = users_col.insert_one({"name": name, "email": email, "password": hashed})
        session["user_id"] = inserted.inserted_id
        return jsonify({"success": True, "message": "Registered successfully."})

    # GET: show simple signup form rendered inside base.html
    signup_html = """
    <form id="signupForm" class="card small-card">
      <label>Name<input name="name" required></label>
      <label>Email<input name="email" type="email" required></label>
      <label>Password<input name="password" type="password" required></label>
      <button type="submit" class="btn">Sign up</button>
      <div id="signupMsg" class="form-msg"></div>
    </form>
    """
    user = current_user()
    return render_template("base.html", page_title="Signup", user=user, content_title="Create account", content=signup_html)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json() or request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password required."}), 400

        user = users_col.find_one({"email": email})
        if not user or not check_password_hash(user["password"], password):
            return jsonify({"success": False, "message": "Invalid credentials."}), 401

        session["user_id"] = user["_id"]
        return jsonify({"success": True, "message": "Logged in."})

    login_html = """
    <form id="loginForm" class="card small-card">
      <label>Email<input name="email" type="email" required></label>
      <label>Password<input name="password" type="password" required></label>
      <button type="submit" class="btn">Log in</button>
      <div id="loginMsg" class="form-msg"></div>
    </form>
    """
    user = current_user()
    return render_template("base.html", page_title="Login", user=user, content_title="Sign in", content=login_html)

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))

@app.route("/purchase")
def purchase():
    user = current_user()
    book_id = request.args.get("book_id", type=int)
    book = next((b for b in BOOKS if b["id"] == book_id), None)
    if not book:
        return render_template("base.html", page_title="Not found", user=user,
                               content_title="Book not found", content="<p>Book not found.</p>"), 404

    if not user:
        # redirect to login with next param
        return redirect(url_for("login") + "?next=" + url_for("purchase") + f"?book_id={book_id}")

    # Simulate purchase flow - in production integrate payment gateway
    confirmation = f"<p>Thanks {user['name']}. You purchased <strong>{book['title']}</strong> by {book['author']} for ₹{book['price']}.</p>"
    return render_template("base.html", page_title="Purchase", user=user, content_title="Purchase complete", content=confirmation)

# Small API to check auth status used by client JS
@app.route("/api/auth-status")
def auth_status():
    user = current_user()
    if not user:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "name": user.get("name"), "email": user.get("email")})

if __name__ == "__main__":
    app.run(debug=True)
