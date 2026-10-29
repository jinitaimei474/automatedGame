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
            description="自动出牌、结算并匹配下一局，完成预设局数后停止。",
            parameters=(
                TaskParameter(
                    key="targetRounds",
                    label="目标对局数",
                    type="integer",
                    required=True,
                    default_value=2,
                    min=1,
                    max=1000,
                    unit="局",
                    description="不论胜负，完成指定局数后自动停止，不再匹配下一局",
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

