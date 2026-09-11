# 皇室战争预标注人工复核方法

本流程用于复核 `datasets/prelabels_gpt56sol` 中的 YOLO 草稿。所有图片初始状态都是 `pending`，只有人工确认后才能作为训练真值。

## 一、打开与排序

1. 使用 CVAT、Label Studio 或 LabelImg，以 YOLO Detection 格式导入 `images`、`labels` 和 `classes.txt`。
2. 先打开 `review_queue.csv`，按 `priority` 排序：`high` → `medium` → `low`。
3. 同一 `session_group` 连续审核，不要随机跳帧。连续帧可以复制上一帧标签，但每一帧仍需目视确认。

LabelImg 示例：打开 `images` 目录，把保存目录设为 `labels`，类别文件选择 `classes.txt`，格式切换为 YOLO。

## 二、每张图片的固定检查顺序

1. **删除错类**：先确认场景类是否正确。搜索对手界面才是 `matching_screen`；VS 对阵卡、竞技场空场与“开战”提示属于 `battle_screen`。
2. **收紧边界**：框紧贴目标可见外缘，四周留白不超过目标宽高的 1%。整页状态类可使用覆盖几乎全屏的框。
3. **补漏标**：从左上到右下扫一遍，补上当前 34 类中实际可见且可可靠判断的目标。
4. **处理遮挡**：目标仍可可靠判断时标注其可见外缘；类别无法确定时删除，不要猜。
5. **记录状态**：在 `review_queue.csv` 把 `review_status` 改成 `approved`（无需修改）、`corrected`（已修改）或 `rejected`（图片不可用），并填写 `reviewer`；必要时写 `review_notes`。

## 三、三个重点场景的判定规则

### 商店与每日精选

- 整个商店页标 `shop_screen`。
- “每日精选”标题条标 `daily_trader`；标题已滚出画面时不要凭商品列表臆造标题框。
- 免费商品卡标 `free_item`；明确显示“免费”时另标 `free_label`；已经领取后的绿色勾/“已收集”标 `claimed_state`。
- 每个完整可见的金币、宝石或现金价格分别紧框为 `currency_price`，不要把数量、卡牌等级或库存进度误标成价格。
- 只有实际可点击的领取控件才标 `claim_button`；付费确认弹窗才标 `payment_confirmation`。

### 游戏模式选择

- 模式抽屉整体标 `game_mode_panel`，不包含被压暗的主页背景。
- “经典1对1”卡片完整可见时标 `classic_1v1`；只露出一小条或被标题栏大幅遮挡时删除该框。
- 不要把经典2对2、经典挑战、终极挑战误标为 `classic_1v1`。

### 开局、结束、胜利与失败

- VS 对阵、空场、国王塔出现和“开战”提示标 `battle_screen`。
- “对战结束”、皇冠飞入与最终双方结算板标 `battle_end`。
- 只有最终皇冠比较已经明确时才额外标 `victory_screen` 或 `defeat_screen`；动画尚未稳定时只保留 `battle_end`。
- `result_crowns_0`～`result_crowns_3` 表示**己方最终皇冠总数的完整结果区域**。看不清或仍在飞入动画时不要标。
- 单个亮起或未亮起皇冠可补 `result_crown_active` / `result_crown_inactive`，但不得把通行证、奖励或主页皇冠算进去。

## 四、质检与数据划分

- 第一轮：一人逐图复核 681 张，所有框和类别都必须看过。
- 第二轮：另一人复核全部验证集/测试集，并至少复核训练集的 20%；重点检查胜负、0～3 皇冠、免费/付费和相邻类别混淆。
- 质检目标：错类率 0%；明显漏标率低于 1%；框边界偏差不超过目标宽高的 3%；`pending` 数量为 0。
- 按 `session_group` 划分训练、验证和测试集。同一视频或同一模拟器连续会话不得跨集合，防止相邻帧泄漏。
- 完成拆分后运行 `python automation/training/clash_royale/check_dataset.py`，再训练并查看每类 precision、recall、mAP 和混淆矩阵。
