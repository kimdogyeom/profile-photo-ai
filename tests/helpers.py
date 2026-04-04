import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"

for path in (ROOT, BACKEND_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def load_repo_module(relative_path: str, module_name: str, clear_modules=None):
    for name in clear_modules or []:
        sys.modules.pop(name, None)

    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_lambda_context(request_id: str = "test-request"):
    return SimpleNamespace(
        function_name="test-function",
        memory_limit_in_mb=128,
        invoked_function_arn="arn:aws:lambda:ap-northeast-1:123456789012:function:test-function",
        aws_request_id=request_id,
    )
