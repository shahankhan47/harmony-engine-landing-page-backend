import os

import anthropic
from openai import AsyncOpenAI

from app.models.models import AsyncRateLimiter

"""Update to support codebases after testing"""
TEXT_FILE_EXTENSIONS = {
    '.dart', '.md', '.markdown', '.js', '.ts', '.py', '.cs', '.cpp', '.c', '.h', 
    '.hpp', '.java', '.kt', '.kts', '.rb', '.php', '.html', '.css', 
    '.scss', '.less', '.xml', '.json', '.yml', '.yaml', '.toml', 
    '.ini', '.cfg', '.txt', '.sh', '.bat', '.ps1', '.rs', '.go', 
    '.swift', '.m', '.mm', '.pl', '.pm', '.r', '.jl', '.scala', 
    '.lua', '.sql', '.erl', '.hrl', '.ex', '.exs', '.dart', '.groovy', 
    '.f90', '.f95', '.f03', '.f08', '.vb', '.vbs', '.asm', '.s', 
    '.lhs', '.hs', '.tsx', '.jsx', '.vue', '.ada', '.adb', '.ads', 
    '.d', '.e', '.factor', '.forth', '.ftl', '.ml', '.mli', '.mlp', 
    '.mly', '.pp', '.pwn', '.pug', '.razor', '.cshtml', '.tpl', '.agc', '.ipynb'
}


DEFAULT_IGNORE_PATTERNS = [
    # Directories
    'node_modules', 'venv', '.git', '__pycache__',  'build',  'dist',
    # File types
    '*.pyc',  '*.pyo',  '*.so',   '*.o',   '*.obj',   '*.exe',   '*.dll',   '*.bin',   '*.log',   '*.tmp',   '*.bak',
    #Flutter
    '.dart_tool', '.flutter-plugins', '.flutter-plugins-dependencies', '.plugin_symlinks', 'build', '*.g.dart',  '*.freezed.dart',  '*.mocks.dart', '*.config.dart',  'ios/Pods', 'android/.gradle'
]

TOKEN_LIMIT = 170000 # based on open ai

API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "x-api-key"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
OPEN_AI_CLIENT = AsyncOpenAI(api_key=OPENAI_API_KEY)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv"}
CLIENT = anthropic.Anthropic()
CLIENT.api_key = os.getenv('ANTHROPIC_API_KEY')
RATE_LIMITER = AsyncRateLimiter(150)
SENDER_EMAIL = "sai_002@harmonyengine.ai"
SMTP_SERVER = "smtp.fastmail.com"
SMTP_PORT = 465  
SENDER_PASSWORD = os.environ.get('EMAIL_PASSWORD')
STARTER_PROJECT_GITHUB_URL = os.getenv('STARTER_PROJECT_GITHUB_URL', "https://github.com/chrislgarry/Apollo-11")