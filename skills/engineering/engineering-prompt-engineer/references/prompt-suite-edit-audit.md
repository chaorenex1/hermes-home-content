# 成组提示词编辑与结构审计

适用：一个插件/服务的多个 LLM 角色提示词共存于代码（常量或 `.md` 模板），共享概念（标记类型、证据等级、advisory target）必须一致。

## 1. 词汇单一来源

```python
# prompting.py —— 最轻量的共享模块
MARKER_TYPES = (
    ("entities", "named people, organizations, services, systems or devices, and why they matter here"),
    ("trajectories", "an ongoing goal or plan and its current state"),
    ("experiences", "a reusable lesson, procedure or outcome proven by the evidence"),
    ("tools", "a tool, command or API and the context in which it worked or failed"),
    ("projects", "a project, repository or workspace and its status"),
)

def marker_glossary(bullet="  * "):
    width = max(len(k) for k, _ in MARKER_TYPES)
    return "\n".join(f"{bullet}{k.ljust(width)} {m}" for k, m in MARKER_TYPES)

def marker_section(heading="VALUE MARKERS — DEFINITIONS", bullet="  * "):
    return f"{heading}\n{marker_glossary(bullet)}"
```

- 消费方：`BASE_SUMMARY_SYSTEM_PROMPT = """...""" + "\n\n" + marker_section()`。
- 正文里留一句指针：`Each type is defined under VALUE MARKERS — DEFINITIONS at the end of this prompt.`
- 概念相同但语义不同时（例如 AI 卡的 `[entity]` 标签 vs 持久 marker），用同一 glossary、不同 heading，并补一句「标签是会话标签，另一个 pass 会存成 marker」，否则模型会多输出顶层键。
- 定义表放在末尾还是插入正文：插入要占位符替换，放末尾只需一次拼接；多个变体（cold / audit / reconcile）由同一常量组装，自动继承。

## 2. 为什么不能 f-string 化

JSON 契约里的 `{` `}` 在 f-string 与 `.format()` 下都要转义；契约越长越容易漏，漏了就变成运行时 `KeyError` 或错位输出。拼接保留原文，diff 也最小。

## 3. 章节骨架

```
ROLE           角色 + 你不是什么 + 你拥有哪些字段
INPUTS         消息里会给你哪些带标签的数据块
WORKFLOW       编号步骤；第 1 步的读入顺序必须等于实际拼接顺序
TRUST ORDER    证据等级与冲突裁决（若角色只有单一来源则并入 ROLE）
OUTPUT CONTRACT  仅一个 JSON / 仅一个对象；键、上限、语言规则
DOMAIN RULES   DRIFT REVIEW / ADVICES / BASE CORRECTIONS 等领域判断
DEFINITIONS    共享词汇表（由 marker_section() 生成）
```

## 4. 交叉核对表（每加一句强断言就查一次）

| 提示词断言 | 必须核对的代码 |
| --- | --- |
| 「唯一的证据是 X」 | 构造 user message 的函数：是否还有 anchor / history / chunk 块 |
| 「先读 A 再读 B」 | `parts = [...]` 的真实追加顺序 |
| 「只能改 N 个字段」 | 写回白名单（如 `_DIALECTIC_FIELDS`） |
| 「上限 k 条 / n 字符」 | 解析器的 truncate / 切片常量 |
| 「target 取下列值」 | 代码里的枚举与降级规则（非法值落到哪） |
| 「用 [unknown] 占位」 | 写回路径是否过滤占位符 |

## 5. 结构审计清单（常见缺陷族）

- **枚举漂移**：提示词 target 枚举 vs 代码校验/降级。两个通道（长期 review 与 live adviser）target 词表不同却都注入同一 agent 时，至少在报告里点名。
- **占位符泄漏 / 字段无法清空**：提示词要求 `[unknown] …` 填充，写回必须过滤；若「全 unknown 即丢弃」，则 reviewer 永远无法把该字段减到空（base 侧却允许 `[]`）——这是设计缺口，不是提示词措辞问题，要报「待决策」。
- **边界不对齐**：提示词比解析器更严属于安全偏差，报告注明即可；解析器比提示词更宽会产生静默截断。
- **模板围栏**：`.md` 模板里 ``` 的配对；一处不闭合会吞掉后面所有 section（`_REQUIRED_HEADINGS` 校验也照不到）。
- **注入防御两层**：系统提示词的信任声明 + `data_block` 标签清洗；缺一层就退化成「靠模型自觉」。
- **空输出合法性**：reviewer 类提示词必须显式允许沉默/空数组，否则模型被迫编建议。
- **章节膨胀**：每加一段都要问它属于哪个角色；复述别的角色职责会让模型越权输出键。

## 6. 验证

```bash
# ① 实读渲染后的章节顺序
python - <<'PY'
import sys; sys.path.insert(0, 'plugin')
import <pkg>.worker as w
for name in ('BASE_SUMMARY_SYSTEM_PROMPT', 'DIALECTIC_SYSTEM_PROMPT'):
    t = getattr(w, name)
    print(name, len(t), [l for l in t.splitlines()
                         if l.strip() in ('ROLE', 'WORKFLOW', 'OUTPUT CONTRACT',
                                          'VALUE MARKERS — DEFINITIONS')])
PY

# ② 仓库测试（用当前解释器，不要裸 pytest）
python -m pytest -q --tb=line -p no:cacheprovider

# ③ 证明某个失败是预先存在的：干净 HEAD worktree，不 stash 正在编辑的工作树
git worktree add -q "$W" HEAD && (cd "$W" && python -m pytest -q --tb=line <file>::<test>)
git worktree remove "$W" --force
```

- 隔离跑通过、全量偶发失败 = flake，报告里写明，不要改产品代码迁就。
- `ModuleNotFoundError: hermes_yaml` 这类宿主依赖缺失，先用 HEAD worktree 复现再判定预先存在；`git stash` 会把正在改的提示词一起藏走，容易误判。

## 7. 报告格式

1. **章节新增清单**：`file:line` + 每个角色加了什么（role / entities / workflow），以及共享词汇源的位置。
2. **结构检查**：「已修」列改动与理由；「待决策」列行为影响与需要用户拍板的点（例如空数组语义、target 词表统一）。
3. **验证**：用例数、失败分类（预先存在 / flake / 本次引入）、提示词顺序的实读证据。
