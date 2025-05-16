import os
from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for
from pathlib import Path, PureWindowsPath

app = Flask(__name__, template_folder='pages')

# 配置
BASE_DIR = Path(__file__).parent
MEDIA_FOLDER = BASE_DIR / 'data'
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.mp4', '.webm', '.mov'}

# 转义字符映射表
ESCAPE_SEQUENCES = {
    '\a': '\\a',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
    '\v': '\\v',
    '\\': '\\\\'
}

def is_media_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def get_current_directory_files(directory):
    """仅获取当前目录下的媒体文件（不包括子目录）"""
    media_files = []
    try:
        for item in directory.iterdir():
            if item.is_file() and is_media_file(item.name):
                media_files.append(item.name)
    except Exception as e:
        print(f"Error reading directory {directory}: {e}")
    return sorted(media_files)

def safe_relative_path(base, target):
    """安全地计算相对路径（处理Windows特殊字符问题）"""
    try:
        # 先将路径转换为纯Windows路径格式处理
        base_parts = PureWindowsPath(base).parts
        target_parts = PureWindowsPath(target).parts
        
        # 确保目标路径在基础路径下
        if base_parts != target_parts[:len(base_parts)]:
            return None
            
        return str(Path(*target_parts[len(base_parts):]))
    except Exception as e:
        print(f"Error calculating relative path: {e}")
        return None

def get_media_context(rel_path):
    """获取媒体文件的上下文信息（仅当前目录）"""
    # 处理路径中的特殊字符
    try:
        path = (MEDIA_FOLDER / rel_path).resolve()
    except Exception as e:
        print(f"Error resolving path {rel_path}: {e}")
        return None
    
    if path.is_file():
        # 如果是文件，获取同目录下的所有媒体文件
        directory = path.parent
        current_file = path.name
    else:
        # 如果是目录，获取该目录下的所有媒体文件
        directory = path
        current_file = None
    
    media_files = get_current_directory_files(directory)
    
    if not media_files and current_file is None:
        return None
    
    if current_file:
        try:
            current_index = media_files.index(current_file)
        except ValueError:
            return None
    elif media_files:
        current_index = 0
        current_file = media_files[0]
    else:
        return None
    
    prev_index = current_index - 1 if current_index > 0 else len(media_files) - 1
    next_index = current_index + 1 if current_index < len(media_files) - 1 else 0
    
    # 获取相对路径（安全方式）
    directory_rel = safe_relative_path(MEDIA_FOLDER, directory)
    if not directory_rel:
        return None
    
    # 获取父目录路径用于导航
    parent_dir = str(Path(directory_rel).parent) if directory != MEDIA_FOLDER else None
    
    return {
        'current': current_file,
        'prev': media_files[prev_index],
        'next': media_files[next_index],
        'directory': directory_rel,
        'parent_directory': parent_dir,
        'is_video': Path(current_file).suffix.lower() in {'.mp4', '.webm', '.mov'},
        'files': media_files,
        'current_index': current_index,
        'has_media': bool(media_files)
    }

def is_safe_path(basedir, path):
    """检查路径是否在基础目录内"""
    try:
        basedir = Path(basedir).resolve()
        path = Path(path).resolve()
        return basedir in path.parents or path == basedir
    except:
        return False

@app.route('/')
def index():
    return redirect(url_for('serve_media', path=''))

@app.route('/data/', defaults={'path': ''})
@app.route('/data/<path:path>')
def serve_media(path):
    try:
        # 使用转义字符映射表处理所有需要转义的字符
        for char, escaped in ESCAPE_SEQUENCES.items():
            path = path.replace(char, escaped)
        
        # 构建完整路径并确保它在允许的目录内
        full_path = (MEDIA_FOLDER / path).resolve()
        if not is_safe_path(MEDIA_FOLDER, full_path):
            abort(403)
        
        if full_path.is_file():
            # 如果是文件，直接发送文件
            return send_from_directory(full_path.parent, full_path.name)
        else:
            # 如果是目录，获取媒体文件上下文
            context = get_media_context(path)
            if not context:
                # 如果是空目录，显示空状态
                parent_dir = str(Path(path).parent) if path else None
                return render_template('index.html', 
                                    media_url=None,
                                    context={
                                        'directory': path or '',
                                        'parent_directory': parent_dir,
                                        'has_media': False,
                                        'files': []
                                    })
            
            if context['has_media']:
                # 有媒体文件则显示第一个
                first_file = context['files'][0]
                directory = context['directory']
                return render_template('index.html', 
                                     media_url=f"/data/{directory}/{first_file}",
                                     context=context)
            else:
                # 没有媒体文件只显示目录信息
                return render_template('index.html', 
                                     media_url=None,
                                     context=context)
    
    except Exception as e:
        print(f"Error serving media: {e}")
        return render_template('error.html', message="无法访问请求的资源"), 404

@app.route('/media_context')
def get_media_context_api():
    """API端点，用于获取媒体上下文（用于前后切换）"""
    path = request.args.get('path', '')
    try:
        # 使用转义字符映射表处理所有需要转义的字符
        for char, escaped in ESCAPE_SEQUENCES.items():
            path = path.replace(char, escaped)
            
        context = get_media_context(path)
        if not context:
            abort(404)
        return context
    except Exception as e:
        print(f"Error getting media context: {e}")
        abort(404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8742, debug=True)