# 英雄皮肤（Hero Skin）机制与"自定义单位拿不到皮肤"的边界

## 一句话结论

游戏内英雄皮肤（模型+语音+图标）由引擎按**各文明原生英雄 proto** 下发；皮肤**模型**的映射不在任何可编辑数据里。自定义新 proto（如 GEMOD 的 Explorer2）拿不到皮肤，只能固定外观。想让"玩家所选皮肤+皮肤语音"实际生效，就让出场单位=该文明原生英雄 proto。

## 三件套的落点

| 层 | 位置 | 能否数据化 |
|---|---|---|
| 语音 | `Sound\<英雄proto>_snds.xml` → `<soundtype>`+`<civlogic>`+`<skinlogic><choice name="skinid">`；音效集定义在 `Sound\soundsets.xml` / `soundsetsde.xml` | ✅ 可整文件复制（自制单位的语音同样走这套，如 explorer2_snds.xml） |
| 图标/头像 | `Data\Data\techtreey.xml` 各 `Age0<Civ>` 科技：`<effect type="Data2" subtype="CopyUnitPortraitAndIcon" unittype="英雄proto" skinid="N"><target type="ProtoUnit">deIconXXX</target>`；`deIcon*` 单位只需 dbid/icon/portraiticon | ✅ 可复制/新增 |
| 模型(animfile) | 皮肤 animfile 在全解包数据、exe（ASCII+UTF-16 全查）、各 .bar/UIResources 中 0 引用；客户端换肤流程带 `SkinFilePath`（exe 符号：ExplorerSkinChange / ExplorerSkinID / SkinFilePath / ExplorerSkinError@protounit.cpp、AVBUnitSkinLogicSoundChooser） | ❌ 数据层无落点 |

## 各文明皮肤载体英雄（homecity<Civ>.xml `<heroprotounits>`）

- Explorer（欧洲/美洲/DE 殖民系）、xpAztecWarchief、xpIroquoisWarChief、xpLakotaWarchief、deIncaWarChief、ypMonkChinese/ypMonkIndian(/2)/ypMonkJapanese(/2)、deGeneral、deGeneral2、dePadre（墨西哥 2 个 hero → 存档 heroskinids 也是 2 条）、deEmir、dePrince、deRegent、deHetman、deGrandMaster…
- 这些 proto 都带 `<flag>HeroName2</flag>`，但该旗标只是"名字槽位"的标记，**不是皮肤开关**——自定义单位照抄它也不会获得皮肤。

## 皮肤选择存储（排障/读取用）

- `Users\UserProfile.xml`（UTF-16）：`<setting name="gameplayerNexplorerskinid">N</setting>`（-1=默认）
- 主城存档 `Game\HomeCity_*.xml`（UTF-16）：`<heroname>…</heroname><herodogname/><heroskinids><skinid>-1</skinid>…</heroskinids>`

## 图标/头像数据写法示例（英国 Age0British，techtreey 约 850-863 行）

- skinid 0=SPCLizzie、1=deIconFemaleExplorerBRLovelace、2=deIconExplorerBRWarwick、3=deIconExplorerBRDrake、4=deIconExplorerArctic；法国 0..4=deIconExplorerFRPecaudy / deIconFemaleExplorerFRFernig / SPCBeaumont / deIconFemaleExplorerFRMarianne / deIconExplorerArctic。
- 自建"多皮肤图标"：照抄写法，unittype 换成目标 proto、skinid 换序号，target 指向 `deIcon*` 单位。

## 皮肤模型文件（供固定外观/复用，不解决重定向）

`Art\units\explorers\`：b_explorer\{warwick,francis_drake}.xml、o_explorer\sahin.xml、s_explorer\{delgado,pizarro}.xml、female\{lovelace,lizzie,spanish_heroine,flamenco,roxelana,sissi,valkyr,…}\<name>.xml、arctic_explorer 等；均为独立 animfile，可直接被 `<animfile>` 引用（自制单位要固定某种皮肤外观就用它）。

## 判定"某功能能否靠数据实现"的排查方法（通用）

1. 全量、忽略文件类型、按二进制搜解包数据：`rg -uuu -a -l '关键词' G:/AOE3_mod/sourceData`；exe 另用 python 查 **UTF-16LE**（`b'w\x00a\x00r…'`）——只搜 ASCII 会误判"不存在"。
2. 解包完整性：`find Data -iname '*.XMB' | while read f; do b=${f%.XMB}; [ -e "$b" ] || echo "$f"; done`（本机为 0 = 无 XMB-only 遗漏）。
3. .bar 探测：大 bar（Sound.bar ~1.8GB、ArtHomecity ~660MB）整读会超时——按需单查一个 bar 并限时。
4. 判定：字符串只出现在 exe 符号/客户端消息 → 客户端侧、数据层无落点；出现在数据 XML（techtreey/protoy/homecity/…）→ 可数据化。

## 实现路线

- **路线 A（可靠，皮肤+皮肤语音全部原生生效）**：不新建英雄单位；把自定义数值/技能写到各文明原生英雄 proto（protomods `<unit name="英雄" mergeMode="modify">`）；`civmods.xml` 的 `<startingunit>` 恢复原生英雄；同步 AI 里按名引用自定义单位的逻辑（gemodai.xs 的 gemodPUID("Explorer2")）。
- **路线 B（保留自定义单位）**：外观固定（挑一个皮肤 animfile 做 `<animfile>`）；语音按 snds 复制但 skinlogic 是否命中要实测，否则退化为固定音效集；图标/头像可用 CopyUnitPortraitAndIcon 补；想要"换皮肤"体验只能自建科技（SetUnitType/ReplaceUnit/CopyUnitPortraitAndIcon/UpdateVisual）。
- **未验证长尾实验**：把 `homecity<Civ>.xml` 的 `<heroprotounits>` 指向自定义 proto（mod 可整文件覆盖 homecity 文件，社区有先例），看游戏内换肤是否重定向；exe 中无 'heroprotounits' 字样，疑似只影响主城场景，成功率低但成本低。

## 实测清单（10 分钟）

1. 小冲突→英国→大厅/主城把探险家皮肤切到不同 skinid→开局看目标单位的**模型/头像/选择语音**是否变化。
2. 语音变化=skinlogic 命中该单位；模型不变=引擎不认自定义 proto（预期）。
3. `DebugOutputGameData` 确认 snds 已合并；`Age3Log.txt` 搜 `ExplorerSkin`（引擎有 ExplorerSkinError 日志点）。
