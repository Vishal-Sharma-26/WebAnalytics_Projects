import os
import pickle
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client.bookrecs
books_col = db.books

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

def load_books():
    docs = list(books_col.find())
    df = pd.DataFrame(docs)
    # ensure description
    df["description"] = df["description"].fillna("")
    df["_id_str"] = df["_id"].astype(str)
    return df

def train_and_save():
    df = load_books()
    if df.empty:
        print("No books found in DB. Insert sample data first.")
        return
    tfidf = TfidfVectorizer(stop_words="english", max_df=0.8)
    tfidf_matrix = tfidf.fit_transform(df["description"])
    sim_matrix = linear_kernel(tfidf_matrix, tfidf_matrix)  # cosine similarity
    # save
    with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "wb") as f:
        pickle.dump(tfidf, f)
    np.savez_compressed(os.path.join(MODEL_DIR, "content_sim_matrix.npz"), sim_matrix, book_ids=df["_id_str"].values)
    print("Model saved to", MODEL_DIR)

if __name__ == "__main__":
    train_and_save()
