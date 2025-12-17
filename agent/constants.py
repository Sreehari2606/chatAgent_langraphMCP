from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

class Intent(str, Enum):
    GENERATE = "generate"
    DEBUG = "debug"
    EXPLAIN = "explain"
    FILE_READ = "file_read"
    FILE_EDIT = "file_edit"
    FOLDER_LIST = "folder_list"
    CODE_REVIEW = "code_review"
    REFACTOR = "refactor"
    TEST_GEN = "test_gen"
    DOCUMENTATION = "documentation"
    OPTIMIZE = "optimize"
    COMMON = "common"

BLOCKED_PATHS = ["/etc", "/usr", ".env", ".ssh", "C:\\Windows", "C:\\Program Files", "node_modules", "__pycache__", ".git"]

CODE_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "javascript",
    ".tsx": "typescript", ".java": "java", ".cpp": "cpp", ".c": "c", ".cs": "csharp",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".html": "html",
    ".css": "css", ".sql": "sql", ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
}

INTENT_ROUTER: Dict[Intent, Dict[str, Any]] = {
    Intent.FILE_READ: {
        "patterns": [r'read.*file', r'analyze.*file', r'open.*file', r'file:?\s*[A-Za-z]:\\', r'[A-Za-z]:\\.*\.(py|js|ts|html|css|json|txt|md)', r'read and analyze', r'check.*file'],
        "node": "file_read",
        "priority": 1,
    },
    Intent.CODE_REVIEW: {
        "patterns": [r'review.*code', r'code.*review', r'check.*quality', r'best.*practice', r'code.*smell'],
        "node": "code_review",
        "priority": 2,
    },
    Intent.REFACTOR: {
        "patterns": [r'refactor', r'improve.*code', r'clean.*up', r'restructure', r'simplify'],
        "node": "refactor",
        "priority": 3,
    },
    Intent.TEST_GEN: {
        "patterns": [r'generate.*test', r'write.*test', r'create.*test', r'unit.*test', r'test.*case'],
        "node": "test_gen",
        "priority": 4,
    },
    Intent.DOCUMENTATION: {
        "patterns": [r'add.*docstring', r'document.*code', r'add.*comment', r'generate.*doc', r'documentation'],
        "node": "documentation",
        "priority": 5,
    },
    Intent.OPTIMIZE: {
        "patterns": [r'optimize', r'performance', r'faster', r'efficient', r'speed.*up'],
        "node": "optimize",
        "priority": 6,
    },
    Intent.DEBUG: {
        "patterns": [r'debug', r'fix.*bug', r'error', r'not.*working', r'broken'],
        "node": "debug",
        "priority": 7,
    },
    Intent.EXPLAIN: {
        "patterns": [r'explain', r'what.*does', r'how.*work', r'understand'],
        "node": "explain",
        "priority": 8,
    },
    Intent.FOLDER_LIST: {
        "patterns": [r'list.*file', r'show.*file', r'workspace'],
        "node": "folder_list",
        "priority": 9,
    },
    Intent.FILE_EDIT: {
        "patterns": [r'edit.*file', r'modify.*file', r'change.*file', r'update.*file'],
        "node": "file_edit",
        "priority": 10,
    },
    Intent.GENERATE: {
        "patterns": [],
        "node": "understand",
        "priority": 99,
    },
    Intent.COMMON: {
        "patterns": [],
        "node": "common",
        "priority": 100,
    },
}

def get_intent_node(intent: Intent) -> str:
    return INTENT_ROUTER.get(intent, {}).get("node", "common")

def get_routing_map() -> Dict[str, str]:
    return {intent.value: config["node"] for intent, config in INTENT_ROUTER.items()}

@dataclass
class NodeResult:
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
