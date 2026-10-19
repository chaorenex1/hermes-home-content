# MO2 Mod 元数据 (meta.ini) 约定

通过 Python configparser 离线编辑 `meta.ini` 时需注意的关键字段和正确值。

## 游戏来源信息

```ini
[General]
gamename=SkyrimSE               # 必须用短名，不是 "Skyrim Special Edition"
repository=Nexus                # 来源平台
modid=165839                    # Nexus MOD ID
version=1.1                     # 安装版本号
newestversion=1.1               # 最新版本号（格式与 version 一致）
nexusfilestatus=1               # 1=已下载
installationfile=FDE_Fura_Bloodmouth-165839.zip  # 安装源文件名
```

## 分类

MO2 有两个分类字段：

| 字段 | 含义 | 来源 |
|------|------|------|
| `category` | MO2 本地分类 ID | `categories.dat` |
| `nexuscategory` | Nexus 同步分类 ID | Nexus API 返回 |

**Skyrim SE categories.dat 常用 ID：**
- 43 = Followers & Companions
- 30 = Immersion
- 9 = NPC
- 11 = Quests and Adventures
- 34 = Patches

⚠️ `category` 必须匹配 `categories.dat` 中的 ID，不能随意填写。`nexuscategory` 由 MO2 从 Nexus 自动获取时写入（离线安装后为 0）。

## 补充字段（离线安装时缺失）

离线 `mo2_install` 不会写入以下字段，需手动补全：

```ini
ignoredversion=
nexusdescription=
url=
hascustomurl=false
lastnexusquery=
lastnexusupdate=
nexuslastmodified=
converted=false
validated=false
endorsed=0
tracked=0
comments=
color=@Variant(\0\0\0\x43\0\xff\xff\0\0\0\0\0\0\0\0)
```

## 批量编辑方法

```python
import os, configparser

config = configparser.ConfigParser()
config.read(meta_path, encoding='utf-8')
if 'General' not in config:
    config['General'] = {}

config['General']['category'] = '43'
config['General']['nexuscategory'] = '96'
config['General']['gamename'] = 'SkyrimSE'

with open(meta_path, 'w', encoding='utf-8') as f:
    config.write(f)
```

⚠️ configparser 会在 key 后加空格（如 `category = 43`），但 MO2 可以正常解析。
