# 免训练对局配置

真实 1v1 使用模板定位页面和固定卡组，HSV 颜色读取圣水，按优先级选择可支付的牌并点击预设落点。
不识别敌军，不优化胜率。现有界面、ADB、皇冠累计和 Mock 保留。
参考 py-clash-bot 的模板/颜色/规则思路独立实现，没有复制其代码或模板：
https://github.com/pyclashbot/py-clash-bot

## 首次校准

需要本机游戏截图，不能直接使用不同版本、语言或比例的素材。模板数量通常是十几个页面锚点加八张卡面；无需 YOLO 数据集。
`assets/clash_royale/` 附带已在本机 MuMu 国服测试的固定卡组模板，安装包会自动复制。不同卡组或界面需按以下步骤重新校准。
使用项目的 `.venv-win\Scripts\python.exe` 或安装 requirements.txt 的 Python。

1. 设置 ADB 路径和设备序列号，使用界面“测试截图”保存截图。分别保留主页、模式选择、战斗、结算 0/1/2/3 皇冠等截图。
2. 初始化配置（不会覆盖已有文件）：

```powershell
python -m automation.training.clash_royale.profile_tool init --image home.png
```

3. 裁剪稳定的按钮/锚点。以下坐标只是命令示例，必须替换成截图上真实的左上/右下坐标：

```powershell
python -m automation.training.clash_royale.profile_tool template --image home.png --label game_mode_button_1 --roi 20 100 80 140
```

必须录入：`home_screen`、`game_mode_button_1`、`classic_1v1`、`battle_button`、`battle_screen`、`battle_end`、`continue_button`、`result_crowns_0` 到 `result_crowns_3`。
按当前页面补充 `play_again_button`、`reward_popup`、`close_button`、`dismiss_popup_button`（评分等已校准弹窗的关闭按钮）。
设置 `require_mode_ready: true` 时还必须提供 `classic_mode_ready`，选完模式后先核对主页图标再开始匹配。
`home_screen`/`battle_screen` 使用该页面独有、稳定的图标，不要截整个画面。
皇冠模板要包含**我方全部三个皇冠槽**，四张模板使用相同范围；只截一个皇冠会混淆结果。
按钮模板中心必须是可点击区域。模板的 `roi` 默认等于裁剪区域，可手动扩大 JSON 中的搜索范围以容纳位移。
锚点与按钮位置不同时，可增加归一化 `target: [x1, y1, x2, y2]`；仅在锚点匹配后点击此区域中心。
避免把动态数字、粒子特效放进模板。每类可手工增加多条不同 file 的模板。

4. 在战斗截图中标出四个手牌搜索区域和十个圣水格内的小采样区域（避开文字/边框）。索引分别 0–3、0–9，圣水从左到右：

```powershell
python -m automation.training.clash_royale.profile_tool region --kind hand --index 0 --image battle.png --roi 80 800 160 920
python -m automation.training.clash_royale.profile_tool region --kind elixir --index 0 --image battle.png --roi 80 950 85 955
```

四个手牌区域应相同尺寸；卡面截图只截稳定插画部分，不含费用数字/等级/边框，且能在四个搜索区域内找到。
觉醒卡的收藏页与普通手牌头像可能不同。每张牌保留 `file`，可增加 `variants: ["templates/另一个头像.png"]`；各头像仍归为同一张牌。
圣水 HSV 默认 OpenCV 色相 125–175，饱和度/亮度至少 80；按实际截图修改 `elixir_hsv` 和 `elixir_coverage`。

5. 为实际使用的八张牌各录入一次卡面、费用和落点。名字使用小写英文、数字、下划线。
落点是整个屏幕的归一化坐标，须选择该牌合法的位置；普通部队宜选己方固定位置。
第一版尽量选没有额外技能、变费、镜像等机制的普通卡牌。法术/建筑也必须各自配置合适落点。

```powershell
python -m automation.training.clash_royale.profile_tool card --image battle.png --roi 90 810 150 870 --name knight --cost 3 --placement 0.3 0.65 --priority 10
```

6. 预览多张真实截图（无设备输入），检查页面、手牌、圣水、皇冠的输出和框：

```powershell
python -m automation.training.clash_royale.profile_tool preview --image battle.png --output preview.png
python -m automation.training.clash_royale.profile_tool activate
```

`activate` 只验证资源和结构，不能证明识别准确。应覆盖圣水不足/足够、卡牌轮换、四种皇冠和继续按钮。
每次工具修改资源会清除 calibrated，需要重新预览和 activate。未设置完整的圣水区域时预览不输出圣水。
所有校准资源保存于 `config/clash_royale/`，已在 Git 中忽略，请自行备份。

## 运行与停止

设置页选择“模板与颜色”，填写 profile.json 路径，测试识别器后保存、重启，再关闭 Mock。
原来的“测试模型”按钮现在加载所选识别器并验证模板配置，不要求 best.pt。
启动弹窗填写“目标对局数”（1–1000 局）。每次新任务从 0 计数，不论胜负，结算后自动匹配下一局；完成预设局数后停止，绝不再点下一局。设置页“默认对局数”只负责预填，启动时填写的数字优先。
默认每局超时 360 秒。单次出牌十秒未确认时记录警告、等待三秒后继续观察本局；皇冠未识别不影响局数任务。长期无法识别页面、结算无法返回或连接故障仍会停止或暂停。
出牌确认要求对应卡槽换牌，并同时满足圣水下降或连续两帧识别到同一张替换牌。这样可容纳选牌预览与圣水恢复，同时避免对未生效的牌连续点击。
启动时若已在对局中，会接续当前一局；新建局数任务若看到旧结算页，会先退出旧结算，不把上一任务的对局重复计数。暂停时停止动作，停止按钮取消等待。
卡组、分辨率比例或界面版本变化后需要重新校准。相同比例的分辨率会自动缩放。
YOLO 兼容模式仍支持原有页面识别；自动出牌仍需要这份模板卡组配置。

商店任务也支持模板识别，但需要另行配置原有 `daily_trader`、`free_item`、`free_label`、`claimed_state` 等类别；没有完成这些配置时不会自动领取。
建议补充网络、登录、付费确认等阻塞模板，保留现有安全判断。

## 验证范围

自动化测试覆盖合成图像上的模板缩放/区域定位、规则出牌和模拟 ADB 的跨局流程。
它们不等于当前客户端的实机验收；尚未校准的游戏截图、卡牌和圣水颜色必须通过上述预览确认。

本机 MuMu 的实际校准和两局测试记录见 `docs/CLASH_REAL_DEVICE_TEST.zh-CN.md`。
当前本地配置使用三个 `crown_slots` 替代四张完整结果模板：每槽包含归一化 `roi`、`empty_file`、`active_hsv`、`active_coverage` 和 `empty_threshold`。
只有每槽都明确判定为金色皇冠或空槽时才输出总数；当前实机仅验证过 0 皇冠，非零结果还需要对应截图校准；局数任务只要求稳定识别结算页，皇冠可以显示为未识别。
