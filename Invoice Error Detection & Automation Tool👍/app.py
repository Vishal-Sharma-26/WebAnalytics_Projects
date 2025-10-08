import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient, ASCENDING
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["invoice_db"]
invoices_col = db["invoices"]

# ensure an index on invoice_number for duplicates detection and quick lookup
invoices_col.create_index([("invoice_number", ASCENDING)], unique=False)


### Validation logic ###
REQUIRED_FIELDS = ["invoice_number", "supplier", "date", "currency", "line_items", "total_amount"]

def parse_date(date_str):
    # try several common formats; return ISO date string or None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat()
        except Exception:
            continue
    return None

def validate_invoice(inv):
    """
    Returns a dict with:
      - valid: bool
      - errors: list of strings
      - warnings: list of strings
      - computed: inferred fields (like computed_total)
      - fix_suggestions: dict of suggested automatic fixes
    """
    errors = []
    warnings = []
    computed = {}
    fixes = {}

    # check required fields
    for f in REQUIRED_FIELDS:
        if f not in inv or inv[f] in (None, "", []):
            errors.append(f"Missing required field: {f}")

    # invoice number duplicate check
    if "invoice_number" in inv:
        dup = invoices_col.find_one({"invoice_number": inv["invoice_number"]})
        if dup:
            warnings.append("Invoice number already exists in DB. Possible duplicate.")

    # date handling
    if "date" in inv:
        parsed = parse_date(inv["date"]) if isinstance(inv["date"], str) else None
        if not parsed:
            warnings.append("Date format not recognized. Suggest normalizing to YYYY-MM-DD.")
            fixes["date"] = None
        else:
            computed["date_iso"] = parsed
            # if original differs
            if parsed.split("T")[0] != inv["date"]:
                fixes["date"] = parsed.split("T")[0]

    # line items and totals
    line_items = inv.get("line_items", [])
    computed_total = 0.0
    if not isinstance(line_items, list) or len(line_items) == 0:
        errors.append("line_items must be a non-empty list of items.")
    else:
        for i, item in enumerate(line_items):
            # expected fields in item
            if "description" not in item:
                errors.append(f"line_items[{i}].description missing")
            qty = item.get("quantity", 1)
            price = item.get("unit_price")
            # attempt to cast
            try:
                qty = float(qty)
            except Exception:
                errors.append(f"line_items[{i}].quantity invalid: {item.get('quantity')}")
                qty = 0
            try:
                price = float(price)
            except Exception:
                errors.append(f"line_items[{i}].unit_price invalid: {item.get('unit_price')}")
                price = 0
            line_total = round(qty * price, 2)
            computed_total += line_total
            # if an item has provided total, check mismatch
            if "total" in item:
                try:
                    provided = float(item["total"])
                    if abs(provided - line_total) > 0.01:
                        warnings.append(f"line_items[{i}] total mismatch ({provided} vs {line_total}).")
                        # suggest fix
                        fixes.setdefault("line_items", {})[i] = {"total": line_total}
                except Exception:
                    warnings.append(f"line_items[{i}] total invalid: {item.get('total')}")
                    fixes.setdefault("line_items", {})[i] = {"total": line_total}

    computed["computed_total"] = round(computed_total, 2)

    # check invoice total
    if "total_amount" in inv:
        try:
            provided_total = float(inv["total_amount"])
            if abs(provided_total - computed_total) > 0.01:
                errors.append(f"Invoice total mismatch: provided {provided_total} vs computed {computed_total}")
                fixes["total_amount"] = computed_total
        except Exception:
            errors.append("total_amount is not a valid number")
            fixes["total_amount"] = computed_total

    # tax check: if tax_percent provided, see if tax_amount matches
    tax_percent = inv.get("tax_percent")
    tax_amount = inv.get("tax_amount")
    if tax_percent is not None:
        try:
            percent = float(tax_percent)
            expected_tax = round((percent / 100.0) * computed_total, 2)
            computed["expected_tax"] = expected_tax
            if tax_amount is not None:
                try:
                    tamt = float(tax_amount)
                    if abs(tamt - expected_tax) > 0.01:
                        warnings.append(f"Tax amount mismatch: provided {tamt} vs expected {expected_tax}")
                        fixes["tax_amount"] = expected_tax
                except Exception:
                    warnings.append("tax_amount not a number")
                    fixes["tax_amount"] = expected_tax
            else:
                fixes["tax_amount"] = expected_tax
        except Exception:
            warnings.append("tax_percent not a valid number")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "computed": computed,
        "fix_suggestions": fixes
    }


### Routes ###
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/invoices", methods=["POST"])
def create_invoice():
    """
    Accepts JSON body of invoice. Validates and stores in MongoDB.
    If query param ?auto_fix=true, attempt suggested fixes before saving.
    """
    try:
        inv = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON", "details": str(e)}), 400

    res = validate_invoice(inv)
    auto_fix = request.args.get("auto_fix", "false").lower() == "true"
    if not res["valid"] and not auto_fix:
        # return errors and suggestions but don't save
        return jsonify({"status": "rejected", "validation": res}), 400

    # apply fixes if requested
    if auto_fix and res["fix_suggestions"]:
        fixes = res["fix_suggestions"]
        if "date" in fixes and fixes["date"] is not None:
            inv["date"] = fixes["date"]
        if "total_amount" in fixes:
            inv["total_amount"] = fixes["total_amount"]
        if "tax_amount" in fixes:
            inv["tax_amount"] = fixes["tax_amount"]
        if "line_items" in fixes:
            for idx, changes in fixes["line_items"].items():
                for k, v in changes.items():
                    inv["line_items"][int(idx)][k] = v

        # re-validate
        res = validate_invoice(inv)

    # store invoice with timestamp
    inv_record = inv.copy()
    inv_record["_created_at"] = datetime.utcnow().isoformat()
    inserted = invoices_col.insert_one(inv_record)
    inv_record["_id"] = str(inserted.inserted_id)

    return jsonify({"status": "saved", "invoice_id": inv_record["_id"], "validation": res}), 201

@app.route("/api/invoices/<invoice_number>", methods=["GET"])
def get_invoice_by_number(invoice_number):
    doc = invoices_col.find_one({"invoice_number": invoice_number})
    if not doc:
        return jsonify({"error": "not found"}), 404
    doc["_id"] = str(doc["_id"])
    return jsonify(doc)

@app.route("/api/invoices", methods=["GET"])
def list_invoices():
    docs = []
    for d in invoices_col.find().sort("_created_at", -1).limit(100):
        d["_id"] = str(d["_id"])
        docs.append(d)
    return jsonify(docs)

@app.route("/api/validate", methods=["POST"])
def api_validate():
    try:
        inv = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON", "details": str(e)}), 400
    res = validate_invoice(inv)
    return jsonify(res)

# Add Delete Endpoint
@app.route("/api/invoices/<invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    try:
        result = invoices_col.delete_one({"_id": ObjectId(invoice_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Invoice not found"}), 404
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
