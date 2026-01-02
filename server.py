from flask import Flask, request, jsonify, send_from_directory
from agent.graph import will_of_code as code_agent
from agent.mcp_client import list_mcp_tools, call_mcp_tool_sync
from langgraph.types import Command
import os

app = Flask(__name__, static_folder='static')




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
    """Handle chat messages"""
    data = request.json
    message = data.get('message', '')
    
    # Debug logging
    print(f"[DEBUG] Received message: {message}")
    print(f"[DEBUG] file_path: {data.get('file_path', 'NOT PROVIDED')}")
    print(f"[DEBUG] file_content length: {len(data.get('file_content', '')) if data.get('file_content') else 'NOT PROVIDED'}")
    
    if not message:
        return jsonify({'error': 'No message'}), 400
    
    try:
        # Configuration for checkpointer (requires thread_id)
        config = {"configurable": {"thread_id": "default"}}
        
        # Build initial state
        state = {"user_query": message}
        if data.get('file_path'):
            state["file_path"] = data['file_path']
        if data.get('file_content'):
            state["file_content"] = data['file_content']
            print(f"[DEBUG] Added file_content to state: {len(state['file_content'])} chars")
        
        # Run agent
        result = code_agent.invoke(state, config=config)
        
        return jsonify({
            'response': result.get("llm_result", "No response"),
            'intent': result.get("intent", "unknown"),
            'current_agent': result.get("current_agent", "unknown"),
            'pending_action': result.get("pending_action"),
            'action_data': result.get("action_data"),
            'mcp_logs': result.get("mcp_logs"),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/mcp/tools', methods=['GET'])
def get_mcp_tools():
    """Get list of available MCP tools from consolidated client"""
    tools = list_mcp_tools()
    return jsonify({'tools': tools})


@app.route('/api/confirm', methods=['POST'])
def confirm_action():
    """Handle accept/reject for code changes and file operations.
    - For code edits: Accept = update editor (temporary), user must Save
    - For delete: Accept = actually delete the file via MCP
    """
    data = request.json
    action = data.get('action', '')
    action_data = data.get('action_data', {})
    action_type = action_data.get('type', 'code_edit')
    
    config = {"configurable": {"thread_id": "default"}}
    
    # Handle delete action immediately (destructive)
    if action == 'accept' and action_type == 'delete':
        path = action_data.get('path', '')
        if path:
            result = call_mcp_tool_sync("delete_file", path=path)
            if result and not result.startswith("ERROR"):
                return jsonify({
                    'success': True,
                    'message': f'File deleted: {path}',
                    'response': f'File `{path}` has been deleted.',
                    'action': action
                })
            else:
                return jsonify({'success': False, 'error': f'Delete failed: {result}'}), 500
    
    # Handle run_python action
    if action == 'accept' and action_type == 'run_python':
        code = action_data.get('code', '')
        if code:
            result = call_mcp_tool_sync("run_python", code=code)
            return jsonify({
                'success': True,
                'message': 'Python code executed',
                'response': f'**Execution Result:**\n```\n{result}\n```',
                'action': action
            })
        else:
            return jsonify({'success': False, 'error': 'No code provided'}), 400
    
    # Resume the LangGraph by providing the user's action to the interrupt
    try:
        result = code_agent.invoke(Command(resume=action), config=config)
        
        if action == 'accept':
            message = "Changes applied to editor. Click Save to write to file."
        else:
            message = "Changes rejected."
            
        return jsonify({
            'success': True, 
            'message': message,
            'response': message,
            'action': action
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        if action == 'accept':
            return jsonify({
                'success': True, 
                'message': 'Changes applied to editor. Click Save to write to file.',
                'action': action
            })
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/files', methods=['GET'])
def list_files():
    """List files in a directory"""
    path = request.args.get('path', os.path.expanduser('~'))
    
    try:
        if not os.path.exists(path):
            return jsonify({'error': 'Path not found'}), 404
        if not os.path.isdir(path):
            return jsonify({'error': 'Not a directory'}), 400
        
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                items.append({
                    'name': item,
                    'path': item_path,
                    'isDirectory': os.path.isdir(item_path),
                    'extension': os.path.splitext(item)[1].lower()
                })
            except:
                continue
        
        # Sort: folders first, then files
        items.sort(key=lambda x: (not x['isDirectory'], x['name'].lower()))
        
        return jsonify({
            'currentPath': path,
            'parentPath': os.path.dirname(path),
            'items': items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/read', methods=['GET'])
def read_file():
    """Read a file"""
    path = request.args.get('path', '')
    
    if not path or not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return jsonify({
            'path': path,
            'content': content,
            'filename': os.path.basename(path)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/write', methods=['POST'])
def write_file():
    """Write to a file"""
    data = request.json
    path = data.get('path', '')
    content = data.get('content', '')
    
    if not path:
        return jsonify({'error': 'No path'}), 400
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'path': path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/drives', methods=['GET'])
def list_drives():
    """List available drives (Windows)"""
    import platform
    import string
    
    if platform.system() == 'Windows':
        drives = [{'name': f"{d}:", 'path': f"{d}:\\"} 
                  for d in string.ascii_uppercase 
                  if os.path.exists(f"{d}:\\")]
        return jsonify({'drives': drives})
    return jsonify({'drives': [{'name': '/', 'path': '/'}]})


if __name__ == '__main__':
    print("Starting WillOfCode on http://localhost:5000")
    app.run(debug=True, port=5000)
