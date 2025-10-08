from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client.bookrecs
books_col = db.books
users_col = db.users

# sample books
books = [
    {"title": "Deep Learning Basics", "author": "A. Author", "description": "Neural networks, backpropagation, deep learning fundamentals.", "price": 299, "cover": "/static/covers/dl.jpg", "purchase_count": 5},
    {"title": "Python for Data Analysis", "author": "W. McKinney", "description": "Pandas, NumPy, data cleaning and manipulation with Python.", "price": 199, "cover": "/static/covers/python.jpg", "purchase_count": 8},
    {"title": "Economic History", "author": "B. Economist", "description": "History of economic thought and modern macroeconomics.", "price": 149, "cover": "/static/covers/econ.jpg", "purchase_count": 2},
    {"title": "Intro to Machine Learning", "author": "C. ML", "description": "Supervised and unsupervised learning algorithms and practical examples.", "price": 249, "cover": "/static/covers/ml.jpg", "purchase_count": 10},
    {"title": "Cooking 101", "author": "Chef Good", "description": "Basic cooking techniques, recipes and kitchen skills.", "price": 99, "cover": "/static/covers/cook.jpg", "purchase_count": 1},
]

books_col.insert_many(books)
print("Inserted sample books.")

# sample user
from werkzeug.security import generate_password_hash
if users_col.find_one({"email":"demo@demo.com"}) is None:
    users_col.insert_one({"name":"Demo User","email":"demo@demo.com","password":generate_password_hash("demo123")})
    print("Inserted demo user demo@demo.com / demo123")
else:
    print("Demo user exists.")
