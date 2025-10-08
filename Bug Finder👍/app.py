from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
import os
import re
import ast
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/bugfinder"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mongo = PyMongo(app)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'py', 'js', 'java', 'cpp', 'c', 'cs', 'php', 'rb', 'go', 'ts', 'jsx', 'tsx', 'html', 'css', 'sql'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class CodeAnalyzer:
    def __init__(self):
        self.issues = []
    
    def analyze_python(self, code):
        """Analyze Python code for common issues"""
        issues = []
        lines = code.split('\n')
        
        try:
            # Parse AST for syntax errors
            ast.parse(code)
        except SyntaxError as e:
            issues.append({
                'type': 'Syntax Error',
                'severity': 'Critical',
                'line': e.lineno,
                'message': f"Syntax error: {e.msg}",
                'suggestion': "Fix the syntax error according to Python grammar rules"
            })
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check for common issues
            if 'print(' in line and not line_stripped.startswith('#'):
                issues.append({
                    'type': 'Debug Code',
                    'severity': 'Low',
                    'line': i,
                    'message': "Print statement found - possible debug code",
                    'suggestion': "Remove or replace with proper logging"
                })
            
            if re.search(r'except\s*:', line):
                issues.append({
                    'type': 'Broad Exception',
                    'severity': 'Medium',
                    'line': i,
                    'message': "Bare except clause catches all exceptions",
                    'suggestion': "Specify exception types to catch"
                })
            
            if 'TODO' in line.upper() or 'FIXME' in line.upper():
                issues.append({
                    'type': 'TODO/FIXME',
                    'severity': 'Low',
                    'line': i,
                    'message': "Unfinished code found",
                    'suggestion': "Complete the implementation"
                })
            
            if re.search(r'=\s*None\s*$', line) and 'def ' not in line:
                issues.append({
                    'type': 'None Assignment',
                    'severity': 'Low',
                    'line': i,
                    'message': "Variable assigned to None",
                    'suggestion': "Consider initializing with appropriate default value"
                })
        
        return issues
    
    def analyze_javascript(self, code):
        """Analyze JavaScript code for common issues"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check for console.log
            if 'console.log(' in line and not line_stripped.startswith('//'):
                issues.append({
                    'type': 'Debug Code',
                    'severity': 'Low',
                    'line': i,
                    'message': "Console.log statement found - possible debug code",
                    'suggestion': "Remove or replace with proper logging"
                })
            
            # Check for == instead of ===
            if '==' in line and '===' not in line and '!=' in line and '!==' not in line:
                issues.append({
                    'type': 'Weak Comparison',
                    'severity': 'Medium',
                    'line': i,
                    'message': "Use strict equality (===) instead of loose equality (==)",
                    'suggestion': "Replace == with === and != with !=="
                })
            
            # Check for var usage
            if re.search(r'\bvar\s+', line):
                issues.append({
                    'type': 'Deprecated Syntax',
                    'severity': 'Low',
                    'line': i,
                    'message': "Using 'var' keyword - consider 'let' or 'const'",
                    'suggestion': "Use 'let' for variables or 'const' for constants"
                })
            
            # Check for missing semicolon
            if line_stripped and not line_stripped.endswith((';', '{', '}', ')', ']')) and not line_stripped.startswith('//'):
                if re.search(r'(return|break|continue)\s*\w', line):
                    issues.append({
                        'type': 'Missing Semicolon',
                        'severity': 'Low',
                        'line': i,
                        'message': "Missing semicolon",
                        'suggestion': "Add semicolon at the end of the statement"
                    })
        
        return issues
    
    def analyze_generic(self, code, file_extension):
        """Generic analysis for any code"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for long lines
            if len(line) > 120:
                issues.append({
                    'type': 'Long Line',
                    'severity': 'Low',
                    'line': i,
                    'message': f"Line too long ({len(line)} characters)",
                    'suggestion': "Break long lines for better readability"
                })
            
            # Check for trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append({
                    'type': 'Trailing Whitespace',
                    'severity': 'Low',
                    'line': i,
                    'message': "Trailing whitespace found",
                    'suggestion': "Remove trailing spaces/tabs"
                })
            
            # Check for tabs and spaces mixed
            if '\t' in line and '    ' in line:
                issues.append({
                    'type': 'Mixed Indentation',
                    'severity': 'Medium',
                    'line': i,
                    'message': "Mixed tabs and spaces for indentation",
                    'suggestion': "Use consistent indentation (either tabs or spaces)"
                })
        
        return issues
    
    def analyze_code(self, code, filename):
        """Main analysis function"""
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
        all_issues = []
        
        # Language-specific analysis
        if file_extension == 'py':
            all_issues.extend(self.analyze_python(code))
        elif file_extension in ['js', 'jsx']:
            all_issues.extend(self.analyze_javascript(code))
        
        # Generic analysis for all files
        all_issues.extend(self.analyze_generic(code, file_extension))
        
        return all_issues

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_code():
    try:
        if 'file' in request.files:
            # File upload
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'File type not supported'}), 400
            
            filename = secure_filename(file.filename)
            code = file.read().decode('utf-8')
        
        elif request.json and 'code' in request.json:
            # Direct code input
            code = request.json['code']
            filename = request.json.get('filename', 'code.py')
        
        else:
            return jsonify({'error': 'No code or file provided'}), 400
        
        if not code.strip():
            return jsonify({'error': 'Empty code provided'}), 400
        
        # Analyze the code
        analyzer = CodeAnalyzer()
        issues = analyzer.analyze_code(code, filename)
        
        # Save analysis to database
        analysis_result = {
            'filename': filename,
            'code': code,
            'issues': issues,
            'created_date': datetime.utcnow(),
            'total_issues': len(issues),
            'severity_count': {
                'Critical': len([i for i in issues if i['severity'] == 'Critical']),
                'High': len([i for i in issues if i['severity'] == 'High']),
                'Medium': len([i for i in issues if i['severity'] == 'Medium']),
                'Low': len([i for i in issues if i['severity'] == 'Low'])
            }
        }
        
        result = mongo.db.analyses.insert_one(analysis_result)
        analysis_result['_id'] = str(result.inserted_id)
        
        return jsonify(analysis_result), 201
    
    except UnicodeDecodeError:
        return jsonify({'error': 'Unable to decode file. Please ensure it\'s a text file.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyses', methods=['GET'])
def get_analyses():
    try:
        analyses = list(mongo.db.analyses.find().sort('created_date', -1).limit(50))
        
        for analysis in analyses:
            analysis['_id'] = str(analysis['_id'])
            # Don't return full code in list view for performance
            analysis.pop('code', None)
            
        return jsonify(analyses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyses/<analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    try:
        analysis = mongo.db.analyses.find_one({'_id': ObjectId(analysis_id)})
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
            
        analysis['_id'] = str(analysis['_id'])
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyses/<analysis_id>', methods=['DELETE'])
def delete_analysis(analysis_id):
    try:
        result = mongo.db.analyses.delete_one({'_id': ObjectId(analysis_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Analysis not found'}), 404
            
        return jsonify({'message': 'Analysis deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_analyses = mongo.db.analyses.count_documents({})
        
        # Get severity distribution across all analyses
        pipeline = [
            {'$unwind': '$issues'},
            {'$group': {'_id': '$issues.severity', 'count': {'$sum': 1}}}
        ]
        severity_dist = list(mongo.db.analyses.aggregate(pipeline))
        
        # Get issue type distribution
        type_pipeline = [
            {'$unwind': '$issues'},
            {'$group': {'_id': '$issues.type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        issue_types = list(mongo.db.analyses.aggregate(type_pipeline))
        
        return jsonify({
            'total_analyses': total_analyses,
            'severity_distribution': severity_dist,
            'top_issue_types': issue_types
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)