"""分类规则接口。"""

import json
from pathlib import Path

from flask import Blueprint, current_app, g, request

from app.services.rule_service import RuleService
from app.utils.auth_decorator import admin_required, login_required
from app.utils.response import fail, success

rules_bp = Blueprint("rules", __name__)


def _parse_path() -> dict:
    """解析路径参数（JSON 字符串）。"""
    raw = request.args.get("path", "{}")
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


@rules_bp.get("/version")
@login_required
def get_current_version():
    """获取当前生效的规则版本。"""
    service = RuleService()
    version = service.get_latest_version()
    if not version:
        return success(None, message="尚未导入分类规则")
    return success(
        {
            "id": version.id,
            "version_no": version.version_no,
            "remark": version.remark,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }
    )


@rules_bp.get("/options")
@login_required
def get_rule_options():
    """获取级联下拉选项（大类～包装方式）。"""
    field = request.args.get("field")
    if not field:
        return fail("请指定 field 参数")
    service = RuleService()
    return success(service.get_cascade_options(field, _parse_path()))


@rules_bp.get("/field-meta")
@login_required
def get_field_meta():
    """获取尺寸/卷数/总入数控件类型与选项。"""
    field = request.args.get("field")
    if not field:
        return fail("请指定 field 参数")
    service = RuleService()
    return success(service.get_field_meta(field, _parse_path()))


@rules_bp.post("/import")
@admin_required
def import_rules():
    """从 Excel 导入分类规则（默认读取需求相关样例文件或上传文件）。"""
    service = RuleService()

    if "file" in request.files and request.files["file"].filename:
        file_storage = request.files["file"]
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        save_path = upload_dir / f"rules_{file_storage.filename}"
        file_storage.save(save_path)
        file_path = str(save_path)
        remark = request.form.get("remark", "管理员上传导入")
    else:
        # 默认使用项目内样例文件（开发便利）
        project_root = Path(current_app.root_path).parent.parent
        default_file = project_root / "需求相关" / "分类规则全维度拆分_最新版.xlsx"
        if not default_file.exists():
            return fail("请上传规则 Excel 文件，或确保样例文件存在")
        file_path = str(default_file)
        remark = request.form.get("remark", "样例文件初始化")

    try:
        result = service.import_from_excel(file_path, g.current_user.id, remark=remark)
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        return fail(f"规则导入失败：{exc}", 500)

    return success(result, message="规则导入成功")
