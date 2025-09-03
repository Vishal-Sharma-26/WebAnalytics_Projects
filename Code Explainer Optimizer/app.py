from flask import Flask, render_template, request, jsonify
from datetime import datetime
import time
import json
from models import db_init, UsageRecord, engine, SessionLocal
from analysis.explainer import explain_code
from analysis.optimizer import optimize_code, format_code
from pymongo import MongoClient

app = Flask(__name__)
# MongoDB connection (local or Atlas)
client = MongoClient("mongodb://localhost:27017/Code_Explainer_Optimizer")  # update with your URI
db = client["code_explainer"]
usage_collection = db["usage_records"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analytics')
def analytics_page():
    return render_template('analytics.html')

@app.route('/api/explain', methods=['POST'])
def api_explain():
    payload = request.json or {}
    code = payload.get('code', '')
    language = payload.get('language', 'python')
    start = time.time()
    try:
        from analysis.explainer import explain_code
        explanation = explain_code(code, language=language)
        elapsed = time.time() - start
        usage_collection.insert_one({
            "timestamp": datetime.utcnow(),
            "language": language,
            "code_size": len(code),
            "action": "explain",
            "success": True,
            "latency_ms": int(elapsed * 1000)
        })
        return jsonify({"explanation": explanation})
    except Exception as e:
        usage_collection.insert_one({
            "timestamp": datetime.utcnow(),
            "language": language,
            "code_size": len(code),
            "action": "explain",
            "success": False,
            "latency_ms": int((time.time()-start)*1000),
            "error": str(e)
        })
        return jsonify({"error": str(e)}), 500

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    payload = request.json or {}
    code = payload.get('code', '')
    language = payload.get('language', 'python')
    start = time.time()
    try:
        from analysis.optimizer import optimize_code, format_code
        formatted = format_code(code)
        optimized = optimize_code(formatted, language=language)
        elapsed = time.time() - start

        usage_collection.insert_one({
            "timestamp": datetime.utcnow(),
            "language": language,
            "code_size": len(code),
            "action": "optimize",
            "success": True,
            "latency_ms": int(elapsed * 1000)
        })

        return jsonify({"optimized": optimized, "formatted": formatted})
    except Exception as e:
        usage_collection.insert_one({
            "timestamp": datetime.utcnow(),
            "language": language,
            "code_size": len(code),
            "action": "optimize",
            "success": False,
            "latency_ms": int((time.time()-start)*1000),
            "error": str(e)
        })
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def api_stats():
    total = usage_collection.count_documents({})
    pipeline = [
        {"$group": {
            "_id": "$action",
            "count": {"$sum": 1}
        }}
    ]
    actions = {doc["_id"]: doc["count"] for doc in usage_collection.aggregate(pipeline)}

    avg_pipeline = [
        {"$group": {"_id": None, "avg_size": {"$avg": "$code_size"}}}
    ]
    avg_size_doc = list(usage_collection.aggregate(avg_pipeline))
    avg_size = int(avg_size_doc[0]["avg_size"]) if avg_size_doc else 0

    return jsonify({
        "total_requests": total,
        "avg_code_size": avg_size,
        "actions": actions
    })


if __name__ == '__main__':
    app.run(debug=True)