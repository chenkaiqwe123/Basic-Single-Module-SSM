# Bid 修改记录逻辑核查要点

## 主要观察

1. **对比原值的来源不稳定**  
   你用 `Raw Recommend` 作为“原始 Bid”的对比基准，但该列是在表格展示前由 `Bid` 直接复制出来的。  
   一旦 `Bid` 被你后续的“已确认/待确认”修改覆盖，`Raw Recommend` 仍然保留的是旧值，这会导致：
   - 后续再次编辑时旧值基准可能不符合“最新已确认值”的语义；
   - 记录里的 `old_bid` 可能不是用户当前看到的值。  
   建议改为使用你缓存的 `original_bids_map` 或在确认后同步更新基准列。

2. **缺少“恢复原值”时的撤销逻辑**  
   目前只在 `new_bid != original_bid` 时写入 `pending_bid_changes`，  
   但用户把 `Bid` 改回原值时，没有分支去删除该条 `pending_bid_changes`，会出现“已恢复但仍提示待确认”的情况。  
   建议在 `new_bid == original_bid` 时清理对应 key。

3. **确认后的基准未更新，可能导致重复/混乱**  
   你在确认后把 `pending_bid_changes` 合并进 `bid_changes`，  
   但对比逻辑仍然依赖旧的 `Raw Recommend`，会让“已确认的值”仍被当作“变更”再次检测出来。  
   建议在确认后同步更新“原值基准”（比如更新 `original_bids_map` 或替换 `Raw Recommend`）。

4. **`original_bids_map` 已建立但未使用**  
   你已经缓存了 `original_bids_map`，但目前没有在对比逻辑中使用它。  
   建议用它统一作为 `old_bid` 来源，避免表格多次渲染带来的基准漂移。

## 可能的修正方向（概念）

- 用 `original_bids_map[keyword_id]` 作为 `old_bid` 基准；
- 若用户修改后又改回原值，则从 `pending_bid_changes` 删除；
- “确认修改”后同步更新 `original_bids_map`（或更新 `Raw Recommend`）；
- 如果想保留“已确认值”为新基准，可在确认后将其写入基准 map。

## 参考伪代码（示意）

```python
original_bid = original_bids_map.get(keyword_id)

if original_bid is None:
    continue

if round(new_bid, 2) == round(original_bid, 2):
    pending_bid_changes.pop(keyword_id, None)
else:
    pending_bid_changes[keyword_id] = build_change(...)

# 确认修改时
for kid, change in pending_bid_changes.items():
    original_bids_map[kid] = change["new_bid"]
```

## Command log

- `ls`
- `find .. -name AGENTS.md -print`
- `rg -n "Amazon Ads Bid Manager|Amazon Ads BI|bid_changes" -S .`
- `rg -n "亚马逊广告|Bid管理" -S src doc`
