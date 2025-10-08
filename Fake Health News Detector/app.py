from flask import Flask, render_template, request, redirect, jsonify
from pymongo import MongoClient
import re

app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client.fakeNewsDB
news_collection = db.news

# Simple fake news detector logic
def detect_fake_news(text):
    fake_keywords = ['cure', 'miracle', 'guaranteed', 'instant', 'unverified', 'hoax']
    text_lower = text.lower()
    if any(word in text_lower for word in fake_keywords):
        return "Fake"
    return "Real"

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Predict endpoint
@app.route('/predict', methods=['POST'])
def predict():
    news_text = request.form.get('news_text')
    if news_text:
        result = detect_fake_news(news_text)
        # Store in DB
        news_collection.insert_one({"news": news_text, "prediction": result})
        return jsonify({"prediction": result})
    return jsonify({"error": "No news text provided"})

if __name__ == "__main__":
    app.run(debug=True)