"""无需填写字段规则接口。"""

from pathlib import Path

from flask import Blueprint, current_app, g, request

from app.extensions import db
from app.services.operation_log_service import write_operation_log
from app.services.skip_field_rule_service import SkipFieldRuleService
from app.utils.auth_decorator import admin_required, login_required
from app.utils.response import fail, success

skip_field_rules_bp = Blueprint("skip_field_rules", __name__)


@skip_field_rules_bp.get("/version")
@login_required
def get_current_version():
    """获取当前生效的无需填写字段规则版本。"""
    service = SkipFieldRuleService()
    version = service.get_latest_version()
    if not version:
        return success(None, message="尚未导入无需填写字段规则")
    return success(
        {
            "id": version.id,
            "version_no": version.version_no,
            "remark": version.remark,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }
    )


@skip_field_rules_bp.get("/disabled-fields")
@login_required
def get_disabled_fields():
    """按大类返回禁用字段英文名列表。"""
    category_large = request.args.get("category_large", "")
    service = SkipFieldRuleService()
    fields = service.get_disabled_fields(category_large)
    return success({"fields": fields})


@skip_field_rules_bp.post("/import")
@admin_required
def import_skip_field_rules():
    """从 Excel 导入无需填写字段规则（须上传文件）。"""
    if "file" not in request.files or not request.files["file"].filename:
        return fail("请上传 Excel 文件")

    file_storage = request.files["file"]
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / f"skip_field_rules_{file_storage.filename}"
    file_storage.save(save_path)

    remark = request.form.get("remark", "管理员上传导入")
    service = SkipFieldRuleService()

    try:
        result = service.import_from_excel(str(save_path), g.current_user.id, remark=remark)
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        return fail(f"规则导入失败：{exc}", 500)

    version = service.get_latest_version()
    write_operation_log(
        g.current_user.id,
        "import_skip_field_rules",
        "skip_field_rule_version",
        version.id if version else None,
        {"version_no": result["version_no"], "rule_count": result["rule_count"]},
    )
    db.session.commit()

    return success(result, message="无需填写字段规则导入成功")
