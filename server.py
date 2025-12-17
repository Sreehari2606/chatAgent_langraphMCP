from flask import Flask, request, jsonify, send_from_directory
from agent.graph import code_agent
import os
import platform
import string

app = Flask(__name__, static_folder='static', static_url_path='/static')
BASE_DIR = os.path.expanduser("~")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/styles.css')
def styles():
    return send_from_directory('static', 'styles.css')

@app.route('/script.js')
def script():
    return send_from_directory('static', 'script.js')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    file_path = data.get('file_path', '')
    file_content = data.get('file_content', '')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    try:
        initial_state = {"user_query": user_message}
        if file_path:
            initial_state["file_path"] = file_path
        if file_content:
            initial_state["file_content"] = file_content
        result = code_agent.invoke(initial_state)
        response_data = {
            'response': result.get("llm_result", "No response generated."),
            'confidence': result.get("confidence", 0.7),
            'intent': result.get("intent", "unknown"),
            'needs_clarification': result.get("needs_clarification", False),
            'clarification_question': result.get("clarification_question", ""),
            'pending_action': result.get("pending_action"),
            'action_data': result.get("action_data"),
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/confirm', methods=['POST'])
def confirm_action():
    data = request.json
    action = data.get('action', '')
    action_data = data.get('action_data', {})
    
    if action == 'accept':
        code = action_data.get('code', '')
        path = action_data.get('path', '')
        action_type = action_data.get('type', '')
        
        if path and code:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(code)
                return jsonify({'success': True, 'message': f'✅ Changes applied to {path}'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        else:
            return jsonify({'success': True, 'message': f'✅ {action_type.title()} changes accepted'})
    
    elif action == 'reject':
        return jsonify({'success': True, 'message': '❌ Changes rejected'})
    
    return jsonify({'error': 'Invalid action'}), 400

@app.route('/api/files', methods=['GET'])
def list_files():
    path = request.args.get('path', BASE_DIR)
    try:
        abs_path = os.path.abspath(path)
    except:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path does not exist'}), 404
    if not os.path.isdir(abs_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    try:
        items = []
        for item in os.listdir(abs_path):
            item_path = os.path.join(abs_path, item)
            try:
                is_dir = os.path.isdir(item_path)
                size = os.path.getsize(item_path) if not is_dir else 0
                items.append({'name': item, 'path': item_path, 'isDirectory': is_dir, 'size': size, 'extension': os.path.splitext(item)[1].lower() if not is_dir else ''})
            except (PermissionError, OSError):
                continue
        items.sort(key=lambda x: (not x['isDirectory'], x['name'].lower()))
        return jsonify({'currentPath': abs_path, 'parentPath': os.path.dirname(abs_path) if abs_path != os.path.dirname(abs_path) else None, 'items': items})
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/read', methods=['GET'])
def read_file():
    path = request.args.get('path', '')
    if not path:
        return jsonify({'error': 'No path provided'}), 400
    try:
        abs_path = os.path.abspath(path)
    except:
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.exists(abs_path):
        return jsonify({'error': 'File does not exist'}), 404
    if os.path.isdir(abs_path):
        return jsonify({'error': 'Path is a directory'}), 400
    if os.path.getsize(abs_path) > 1024 * 1024:
        return jsonify({'error': 'File too large (max 1MB)'}), 400
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return jsonify({'path': abs_path, 'content': content, 'filename': os.path.basename(abs_path)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/write', methods=['POST'])
def write_file():
    data = request.json
    path = data.get('path', '')
    content = data.get('content', '')
    if not path:
        return jsonify({'error': 'No path provided'}), 400
    try:
        abs_path = os.path.abspath(path)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'path': abs_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drives', methods=['GET'])
def list_drives():
    if platform.system() == 'Windows':
        drives = [{'name': f"{letter}:", 'path': f"{letter}:\\"} for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]
        return jsonify({'drives': drives})
    return jsonify({'drives': [{'name': '/', 'path': '/'}]})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
