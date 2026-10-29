"""Fixed deck rules; all placements are calibrated, normalized screen coordinates."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CardMove:
    card: str
    slot: int
    select: tuple[int, int]
    placement: tuple[float, float]


class RuleBattlePolicy:
    def __init__(self, deck, cooldown=2.0, acknowledgement_timeout=10.0):
        if len(deck) != 8 or len({card['name'] for card in deck}) != 8:
            raise ValueError('固定卡组必须包含八张不同卡牌')
        for card in deck:
            if not isinstance(card['cost'], int) or not 1 <= card['cost'] <= 10:
                raise ValueError('卡牌费用必须是 1–10 的整数')
            if len(card['placement']) != 2 or not all(0 < x < 1 for x in card['placement']):
                raise ValueError('出牌落点必须是归一化屏幕坐标')
        self.deck = {card['name']: card for card in deck}
        self.cooldown = cooldown
        self.acknowledgement_timeout = acknowledgement_timeout
        self.reset()

    def reset(self):
        self.pending = None
        self.pending_replacement = None
        self.last_play = float('-inf')

    @staticmethod
    def _elixir(detections):
        values = {int(d.label.split('_')[1]) for d in detections if d.label.startswith('elixir_')}
        return next(iter(values)) if len(values) == 1 else None

    def submitted(self, move, detections, now):
        self.pending = (move, self._elixir(detections), now)
        self.pending_replacement = None
        self.last_play = now

    def choose(self, detections, now):
        labels = {d.label for d in detections}
        if 'battle_screen' not in labels or labels & {'battle_end', 'victory_screen', 'defeat_screen'}:
            return None
        elixir = self._elixir(detections)
        if self.pending:
            move, before, sent = self.pending
            cards = [d.label for d in detections if d.label.startswith(f'card_{move.slot}_')]
            replacement = cards[0] if len(cards) == 1 and cards[0] != f'card_{move.slot}_{move.card}' else None
            # Selection previews and regeneration can hide the elixir decrease.
            # Two consistent replacement frames also confirm a completed play.
            stable_replacement = replacement is not None and replacement == self.pending_replacement
            self.pending_replacement = replacement
            if replacement and (stable_replacement or (elixir is not None and before is not None and elixir < before)):
                self.pending = None
            elif now - sent > self.acknowledgement_timeout:
                raise RuntimeError('出牌未确认：手牌和圣水未变化，请检查卡组、落点或颜色校准')
            else:
                return None
        if elixir is None or now - self.last_play < self.cooldown:
            return None
        choices = []
        for slot in range(4):
            cards = [d for d in detections if d.label.startswith(f'card_{slot}_')]
            if len(cards) != 1:
                continue
            detection = cards[0]
            name = detection.label.split('_', 2)[2]
            card = self.deck.get(name)
            if card and card['cost'] <= elixir:
                choices.append((card.get('priority', 0), -slot, CardMove(name, slot, detection.center, tuple(card['placement']))))
        return max(choices, key=lambda item: item[:2])[2] if choices else None
