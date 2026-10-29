# Template and rule battle implementation

User approved implementation in this chat: retain desktop UI and ADB, use templates,
colors and a fixed deck to play, finish and advance matches without optimizing wins.

- [x] Add a profile-based OpenCV detector with normalized ROIs, template resources,
  HSV coverage and strict calibration validation. Preserve Detection output.
- [x] Add fixed-deck card selection with affordability, legal configured placement,
  cooldown and observed deployment acknowledgement. Never play on unknown pages.
- [x] Wire live workflow to battle policy and bounded result navigation; retain crown
  target and add round cap. Make detector selectable without requiring YOLO weights.
- [x] Supply profile authoring/inspection CLI and setup guide; never invent calibrated
  coordinates or claim real-device success using synthetic tests.
- [x] Test image matching, missing resources, resolution mismatch, affordability,
  acknowledgement timeout, cancellation, result transitions and round caps. Run backend
  suite and desktop type/lint checks. Review integration separately.

Implementation choices: profiles require explicit screen dimensions; templates/ROIs use
that reference frame, returned positions scale to the actual image. Refuse aspect-ratio
changes. A deck contains eight named cards, costs, priorities and normalized placements.
Use template-specific thresholds; result classification is mutually exclusive.
Local emulator calibration remains necessary because no verified current UI/deck was supplied.

Review: independent review found pause-during-capture tap race, stale pre-placement
elixir baseline, and invalid color coverage accepting an empty bar as full. All three
were corrected with regression coverage. Paused cancellation also reproduced and fixed.
Backend suite: 45 passed. Desktop checks recorded in the task conversation.
Real device acceptance is pending ADB path, fixed deck and local screenshot calibration.
