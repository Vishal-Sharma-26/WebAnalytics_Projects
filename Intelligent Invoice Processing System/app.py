from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import os
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client.invoiceDB
invoice_collection = db.invoices

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Upload invoice
@app.route('/upload', methods=['POST'])
def upload():
    if 'invoice' not in request.files:
        return jsonify({'status': 'fail', 'message': 'No file part'})
    
    file = request.files['invoice']
    if file.filename == '':
        return jsonify({'status': 'fail', 'message': 'No selected file'})

    filename = secure_filename(file.filename)
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    text = ""
    # If text file, read normally
    if filename.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    # If PDF, use pdfplumber (install: pip install pdfplumber)
    elif filename.endswith('.pdf'):
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    else:
        return jsonify({'status': 'fail', 'message': 'Unsupported file type'})

    # Extract invoice details (simple regex)
    import re
    invoice_number = re.search(r'Invoice Number[:\s]*(\w+)', text)
    invoice_date = re.search(r'Date[:\s]*(\d{2}/\d{2}/\d{4})', text)
    total_amount = re.search(r'Total[:\s]*\$?(\d+\.?\d*)', text)

    invoice_data = {
        'filename': filename,
        'invoice_number': invoice_number.group(1) if invoice_number else None,
        'invoice_date': invoice_date.group(1) if invoice_date else None,
        'total_amount': float(total_amount.group(1)) if total_amount else None
    }

    invoice_collection.insert_one(invoice_data)

    return jsonify({'status': 'success', 'data': invoice_data})



# Dashboard to view invoices
@app.route('/dashboard')
def dashboard():
    invoices = list(invoice_collection.find())
    return render_template('dashboard.html', invoices=invoices)


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
