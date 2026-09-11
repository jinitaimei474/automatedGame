from __future__ import annotations

from automation.core.tasks import TaskParameter
from automation.games.base import TaskDefinition


class ClashRoyalePlugin:
    id = "clash_royale"
    name = "皇室战争"
    package_name = "com.supercell.clashroyale"
    model_path = "automation/games/clash_royale/models/best.pt"
    tasks = (
        TaskDefinition(
            id="classic_1v1_loop",
            name="经典 1v1 循环匹配",
            description="按累计皇冠目标循环对局，达到或超过目标后安全停止。",
            parameters=(
                TaskParameter(
                    key="targetCrowns",
                    label="目标皇冠数量",
                    type="integer",
                    required=True,
                    default_value=10,
                    min=1,
                    max=9999,
                    unit="个",
                    description="本次任务累计获得的皇冠数量达到或超过该值后自动停止",
                ),
            ),
        ),
        TaskDefinition(
            id="daily_shop_free_item",
            name="每日商人免费领取",
            description="仅在同时识别每日商人和免费标识时领取；任何付费迹象立即暂停。",
        ),
    )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "packageName": self.package_name,
            "modelPath": self.model_path,
            "tasks": [task.as_dict() for task in self.tasks],
        }

    def task(self, task_id: str) -> TaskDefinition:
        task = next((item for item in self.tasks if item.id == task_id), None)
        if task is None:
            raise KeyError(f"未知任务: {task_id}")
        return task

