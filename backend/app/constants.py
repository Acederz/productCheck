"""业务常量定义。"""

# 任务状态
TASK_STATUS_UNASSIGNED = "未分发"
TASK_STATUS_PENDING = "待处理"
TASK_STATUS_REVIEW = "待审核"
TASK_STATUS_REJECTED = "已驳回"
TASK_STATUS_APPROVED = "已通过"

TASK_STATUSES = (
    TASK_STATUS_UNASSIGNED,
    TASK_STATUS_PENDING,
    TASK_STATUS_REVIEW,
    TASK_STATUS_REJECTED,
    TASK_STATUS_APPROVED,
)

# 数据平台枚举
PLATFORMS = (
    "淘宝",
    "京东",
    "消费者洞察淘宝",
    "消费者洞察京东",
)

# 角色
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

# Excel 表头（19 列，顺序固定）
EXCEL_HEADERS = (
    "序号",
    "宝贝ID",
    "宝贝主图",
    "宝贝名称",
    "品牌",
    "是否经营",
    "大类",
    "区隔",
    "类别",
    "主材质",
    "辅材质",
    "包装方式",
    "尺寸",
    "卷数",
    "总入数",
    "产品属性",
    "宝贝文描图",
    "宝贝链接",
    "数据平台",
)

# 不可修改字段
READONLY_FIELDS = {
    "row_no",
    "product_id",
    "main_image",
    "product_name",
    "brand",
    "product_attr",
    "desc_images",
    "product_url",
    "platform",
}
