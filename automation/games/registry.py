from __future__ import annotations

from automation.games.clash_royale.game import ClashRoyalePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins = {ClashRoyalePlugin.id: ClashRoyalePlugin()}

    def get(self, game_id: str) -> ClashRoyalePlugin:
        try:
            return self._plugins[game_id]
        except KeyError as exc:
            raise KeyError(f"未知游戏插件: {game_id}") from exc

    def manifest(self) -> list[dict[str, object]]:
        return [plugin.as_dict() for plugin in self._plugins.values()]

