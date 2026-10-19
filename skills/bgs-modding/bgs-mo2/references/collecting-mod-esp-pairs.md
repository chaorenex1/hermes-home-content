# 从 MO2 收集本体+汉化 ESP 配对

从 MO2 modlist 中批量提取 (本体 mod ESP, 汉化 mod ESP) 配对的工作流。

## 触发场景

- 需要将 MO2 中所有有汉化的 mod 的 ESP 导出到外部工具
- 需要收集本体/汉化 ESP 配对用于翻译对比、字串提取等

## 步骤

### 1. 绑定 MO2 并获取数据

```python
# 绑定 session（tri-split 布局注意 mo2Root 指向实例 INI 目录）
mo2_session(mo2Root=INSTANCE_DIR, mo2InstanceRoot=DATA_DIR, profile="pbr")

# 获取 modlist + machine_contract（含所有 mod 根路径）
mo2_modlist(profile="pbr", enrich=True)
mo2_machine_contract()
```

### 2. 识别汉化 mod

汉化 mod 命名模式（简体中文 SSE 生态）：

| 模式 | 示例 |
|------|------|
| `- CHS` / `CHS` | `Embers XD CHS`, `Happy Little Trees - CHS` |
| `- CHS WL` / `CHS WL` | `Follower Dialogue Expansion - Lydia - CHS WL` |
| `- CN` / `CN` | `Daedric Shrines - All in One-CN` |
| `和光` / `With Light` | `Chinese Translation for SkyUI By With Light` |
| `Simplified Chinese` | `Legacy of the Dragonborn SSE Simplified Chinese translation` |
| `LOYI CHS` | `OStim Standalone - LOYI CHS` |
| `Chinese Translation` | `Simple Follower Framework - Chinese Translation` |
| `(CHS)` / `(CN)` | `Landscape Fixes For Grass Mods(CHS)` |

筛选逻辑：

```python
cn_keywords = ["CHS", "和光", "With Light", "CN", "Chinese", "汉化", "简体", "LOYI CHS"]
cn_mods = [m for m in enabled_mods if any(kw in m["name"] for kw in cn_keywords)]
```

### 3. 匹配本体 mod

对每个汉化 mod，通过剥离 CN 后缀找到原始 mod 名：

```python
cn_suffix_patterns = [
    r'\s*[-–—]\s*CHS(?:\s*WL)?(?:\s*ver\.?\s*[\d.]+)?$',
    r'\s*[-–—]\s*CN$',
    r'\s*[-–—]\s*Chinese(?:\s*Translation)?$',
    r'\s+CHS(?:\s*WL)?(?:\s*ver\.?\s*[\d.]+)?$',
    r'\s+CN$',
    r'\s*[-–—]\s*和光.*$',
    r'\s+和光.*$',
    r'\s*[-–—]\s*With\s*Light.*$',
    r'\s+With\s*Light.*$',
    r'\s*[-–—]\s*Simplified\s+Chinese(?:\s*(?:Translation|Version))?$',
    r'\s+Simplified\s+Chinese(?:\s*(?:Translation|Version))?$',
    r'\s*[-–—]\s*CHS(?:\s*WL)?$',
    r'\s*\(CHS\)$',
    r'\s*\(CN\)$',
    r'\s*\(Chinese(?:\s*Translation)?\)$',
    r'\s*[-–—]\s*LOYI\s*CHS$',
    r'\s+LOYI\s*CHS$',
]
```

**特殊映射**：某些汉化 mod 命名不规则，需要硬编码映射表：

```python
special_mappings = {
    "Chinese Translation for Unofficial Skyrim Special Edition Patch By With Light":
        "Unofficial Skyrim Special Edition Patch",
    "Chinese Translation for SkyUI By With Light": "SkyUI",
    # ...
}
```

### 4. 提取 ESP 文件

从 machine_contract 获取每个 mod 的物理路径，遍历查找 `.esp/.esm/.esl`：

```python
# 遍历 mod 目录收集 ESP
for ext in ['*.esp', '*.esm', '*.esl']:
    for f in glob.glob(os.path.join(mod_root, '**', ext), recursive=True):
        esps.append(os.path.basename(f))
```

**注意**：部分 CN mod 的 ESP 列表来自 MCM translation 文件（strings），不是实际 ESP — 这些在磁盘上找不到，会报 "CN ESP not found on disk"。这是正常现象，跳过即可。

### 5. 复制到目标目录

```python
# 本体 ESP → val/, 汉化 ESP → key/
for pair in esp_pairs:
    for cn_esp in pair["cn_esps"]:
        shutil.copy2(cn_esp_path, KEY_DIR / cn_esp)   # 汉化 → key
        if orig_esp_path:
            shutil.copy2(orig_esp_path, VAL_DIR / cn_esp)  # 本体 → val
```

## 常见问题

- **CN mod 无 ESP**：纯字串替换 mod（只有 `.txt`/`.json` translation 文件），跳过
- **同名 ESP 覆盖**：多个 mod 提供同名 ESP 时，最后复制的生效。如需保留全部，在目标文件名中加 mod 名前缀
- **"CN ESP not found on disk"**：该 mod 的 ESP 是引用而非实际文件（如 Oblivion Interaction Icons 的 patch hub），正常跳过
