---
name: aoe3de-mod-development
description: "Use when developing AOE3DE (帝国时代3决定版) mods."
---

# AOE3DE MOD 开发标准流程

适用：用户提出帝国时代3决定版（AOE3DE）MOD 需求时——改单位/科技/卡片/旗军/战术/技能/语音/图标/字符串(汉化)/地图/英雄皮肤。

## 环境地图（本机）

| 项 | 路径 |
|---|---|
| 游戏安装 | <PATH_TO_STEAM_LIBRARY>\steamapps\common\AoE3DE（数据 bar：Game\Data\Data.bar；美术：Game\Art\*.bar；音效 Sound） |
| 用户数据 | <USER_HOME>\Games\Age of Empires 3 DE\76561198302089308\（mods\local\<MOD>、Startup\、mods\age3-mod-status.json 记录各 MOD 的 Priority/Enabled） |
| 工程工作区 | G:\AOE3_mod\workSpace\GEMOD（已启用 git 仓库，改前先 commit）→ 部署到 mods\local\GEMOD（复制保持目录结构） |
| 原版基线（已解包 XML） | G:\AOE3_mod\sourceData\Data\Data（protoy.xml、techtreey.xml、civs.xml、strings\...；另有 .XMB 伴生文件） |
| 圣典参考库 | G:\AOE3_mod\refs\aoebbs_sacred_book\（index.md + md\ 244 页；在线版 https://www.aoebbs.net/tutorial.html） |
| 工具 | G:\AOE3_mod\ResourceManager\Resource Manager.exe（解 bar / XMB↔XML）；G:\AOE3_mod\gr2_viewer.exe（模型查看）；AOE3ED FileConverter（格式转换，质量优于 RM） |

## 核心原则

1. 优先附加式 MOD（Additive Data Mods）：不覆盖原文件、与基础数据合并、游戏更新后不失效。
2. 改数据前先查原版定义：直接 grep G:\AOE3_mod\sourceData\Data\Data 下的 xml（按 name= 或 _locID 字符串 ID），不要重新解包 bar。
3. 每个修改节点显式写 mergeMode，不依赖默认值。
4. 所有改动只落在工程工作区（G:\AOE3_mod\workSpace\GEMOD），再整体同步到 mods\local\GEMOD；不要在游戏安装目录直接改文件。
5. 覆盖式/大改动前先备份目标文件（工程已有 backup_* 目录惯例，merge_mod.ps1 亦先备份）。

## 先读（每次任务第一步）

1. `G:\AOE3_mod\docs\AOE3DE_MOD开发-SOP路由表.md` —— 需求→文件→步骤→验证（A环境/B单位/C科技卡片/D文明/E文本/F地图/G排障）。
2. `G:\AOE3_mod\docs\AOE3DE_MOD标准流程.md` —— 总流程、环境、DE 机制。
3. 按需查 `G:\AOE3_mod\refs\aoebbs_sacred_book\sop_notes\` 分章笔记。

## 标准流程（通用）

1. 归类需求 → 按下表选实现层。
2. 查基线并在工程中定位已有相关节点（避免重复/冲突）。
3. 最小 diff 编写修改（附加式文件优先，保持原文件命名/大小写风格）。
4. 同步部署到 mods\local\GEMOD。
5. 验证：游戏内「工具→模组」确认启用与优先级；必要时用 DebugOutputGameData 对比合并输出（见 references/additive-mods.md）。
6. 记录变更。

| 需求 | 实现层（附加式优先） |
|---|---|
| 单位数值/属性/攻击 | Data\protomods.xml（<Unit name=...>，mergeMode 按需） |
| 科技效果/成本 | Data\techtreemods.xml（<Tech name=...><Effects>） |
| 国家参数/开局资源与单位 | Data\civmods.xml（<civmods>；圣典 18-31 补充字段） |
| 卡片/主城 | homecity<civ>.mods.xml / 主城相关 xml（圣典 6 章以旧版为主，DE 部分不适用） |
| 旗军/捆绑训练 | civs.xml 字段（圣典 4-x；DE 归 civmods.xml） |
| 战术 | Data\tactics\<x>.mods.tactics（对应原 <x>.tactics） |
| 技能/光环/冷却 | Data\abilities\abilitymods.xml、powermods.xml（圣典 9 章） |
| 字符串/汉化 | Data\strings\<语言>\stringmods.xml（如 SimplifiedChinese） |
| 语音 | Sound\ 及相关 snds/playlist xml（非附加式，直接放文件；圣典 5 章） |
| 模型/贴图/animfile | Art\...（gr2 + xml；圣典 8/17 章） |
| 地图 | RandMaps\、XS 脚本（圣典 13 章） |
| 英雄皮肤/英雄自定义 | 仅限各文明原生英雄 proto（见「英雄皮肤/英雄自定义 速查」）；自定义单位拿不到皮肤模型 |
| 自定义界面(UI/HUD) | DE=WPF/XAML：覆盖 Game\UI\UI.bar 的 .xaml（mod Data\wpfg\ 同名整文件替换）；图片 UIResources*.bar → mod Data\wpfg\resources\...；剧情编辑器 ui*.xml → mod Data\（见「自定义UI」速查） | — | 游戏内看画面 |

## 附加式 MOD 速查

- 映射：protoy→protomods.xml、techtreey→techtreemods.xml、civs→civmods.xml、abilities→abilitymods.xml、powers→powermods.xml、tactics→同名 <x>.mods.tactics、strings→stringmods.xml、protounitcommands→protounitcommandmods.xml、nuggets→nuggetmods.xml、cultures→culturemods.xml。
- 根节点=文件名（<protomods>、<techtreemods>…）；mergeMode ∈ modify|add|remove|replace，缺省：能匹配基础节点则 modify 否则 add。
- stringmods 例外：无 mergeMode，直接按 <String _locID> 改。
- 完整映射表、示例与 DebugOutputGameData 验证步骤：references/additive-mods.md。

## 充能攻击（chargeaction/蓄力技能）速查

给单位加充能攻击（如 ChargeCarbineAttack/ChargePistolAttack），四层都要改：

| 层 | 改动 |
|---|---|
| protomods 单位级 | `<rechargetime>20.0000</rechargetime>`（充能CD秒）；可选 `<chargeusagetime>0.2500</chargeusagetime>`（触发后可用窗口，原版 ChargeCarbineAttack 家族统一 0.25）；科技门控另加 `<active>0</active>`+科技 ActionEnable 效果 |
| protoaction | `<name>ChargeCarbineAttack</name>` + `<chargeaction>1</chargeaction>`（伤害/射程/ROF 写这里） |
| tactics | action 定义内加 `<chargeaction>1</chargeaction>`；并在每套 tactic 的 action 列表以高于普通攻击的优先级引用（如 110 > 100，Melee 可不加） |
| abilitymods | `<单位名><ability>deChargeAbilityXxx<bindtochargeaction>true</bindtochargeaction><forceshowrollover>true</forceshowrollover></ability>`；无 `<tech>` = 常驻，有 `<tech>` = 门控。命名对照：ChargeCarbineAttack→deChargeAbilityCarbine；ChargePistolAttack→deChargeAbilityChargedPistol；Zouave 专用名同理 |

- 禁止直接改共享 tactics（musketBayonet.tactics 被原版约 46 个单位引用→改它=波及全部）：必须复制为 `<unit>.tactics` 再把单位 `<tactics>` 指针指向新文件；复制时完整保留原文件全部 action/tactic（潜行、Build、CrateGather、Discover、Stagger 等），只追加充能相关内容。
- action 引用的 anim/reloadanim/idleanim 必须存在于该单位 animfile（查 Art\units\...\<unit>.xml 的 `<anim>` 列表；musket 系单位只有 Volley_standing_* 一套）。
- 单位级 rechargetime/chargeusagetime 均可缺省运行（如 deSpyOttoman 无 chargeusagetime）；写反/漏掉 tactics 侧 chargeaction 则充能完全不生效。**但带 chargeaction 的单位必须至少给 `<rechargetime>`**：无任何 recharge 字段时充能行为异常（攻击/动画反复重放，表现为“动画不能正确播放”）；`<recharge type="Kills">` 与原版仅 deBersagliere 使用，不要与 rechargetime 混用，改时间 CD 时把它替换掉。chargeusagetime 建议 ≥ 一次攻击周期（如火箭 rof3 → 3.0；齐射/手枪类 0.25）。
- 骑马单位的特殊攻击动画：**判定事件全部写马侧，骑手侧只放姿势与武器挂点**。原版攻击事件（`<tag type="Attack">`、SpecificSoundSet、Particles）只写在主 animfile（马/骆驼等主模型文件）里——全原版 83 个 rider 文件 0 个含 Attack tag（范本：us_cavalry_horse、colonial_guardian_horse、reiter_horse）；骑手文件里的 tag 不派发，**漏写马侧 Attack tag 的充能攻击会表现为「有动作、无弹丸、无命中」**。骑手 clip 必须用 cavalry 系列（carbine_attack_a/b、carbine_reload_a..e、pistol_attack_A 等），套步兵 clip（如火焰兵 shared\rocket_attack）会播放错位；配套马侧片段 horse_carbine_attack_a/b（攻击事件点 0.27/0.37，照 us_cavalry_horse）、horse_reload；注意 carbine 的 idle 片段只在 animation_library\cavalry\carbine\carbine_idle_a（顶层只有 attack/reload，顶层无 carbine_idle_a）。武器挂点仍按目标武器抄（launcher/rocket = bone_gun/ATTACHPOINT→Bip01 Prop1 syncanims=1）。
- 验证链：git diff（workSpace/GEMOD git 仓库）→ 部署后 `diff -rq --exclude=.git` 工程 vs mods\local\GEMOD 必须 0 差异 → 游戏内实测（单位每 N 秒自动释放强击）。

## 科技门控与"操作按钮"速查

- 门控蓄力：protoaction 与 tactics action 各加 `<active>0</active>`，tactics 里仍以高优先级引用；科技加 `<effect type="Data" action="<动作名>" amount="1.00" subtype="ActionEnable" relativity="Absolute"><target type="ProtoUnit">单位</target></effect>`；abilitymods 里对应技能加 `<tech>科技名</tech>`。范本：原版 DEHCPapalArsenal（同时启用 ChargePistolAttack/LanceChargeAttack/ChargeCarbineAttack 多单位）、riflemanshield.tactics+deNMPapalZouave 的 ChargeCarbineAttack 门控写法。
- 把可研发科技放到"单位"上（如 GreatBombard2）：proto 里加 `<command page="11" column="0">Abilities</command>` + `<tech row="0" page="11" column="0">科技名</tech>`（范本：deMalteseGun 的 deFixedGunLongRangeAttack）；建成式科技需 `<status>OBTAINABLE</status>` 且不要加 `<flag>HomeCity</flag>`。
- 建筑/单位格子上的"无限次"科技（如 Lombard 投资）：`<cost resourcetype="Ships">1.0000</cost>`（消耗1次船运，建筑挂载可行，范本：AoP 模组 zpHansaTrade* 挂 zpHansaEmbassy）+ `<flag>YPInfiniteTech</flag>`（可反复研究，原版 163 处：Repeat 卡等）+ 年龄前置 `<prereqs><techstatus status="Active">Industrialize</techstatus></prereqs>`（工业时代）。
- 投资资源效果：`<effect type="Data" amount="1200.00" subtype="InvestResource" resource="Food|Wood|Gold" relativity="Absolute"><target type="Player"></target></effect>`（原版样例：DEHCGenoeseFinancers 1200 金 / DEHCLuccanFinancers 1200 木 / DEHCSieneseFinancers 800 食；Lombard 需 InvestmentBuilding 且已启用 InvestmentEnable）。
- 火塔（FireAttack 塔防强化）：范本原版 DEHCFireTowers——`TechStatus active: FrontierOutpost` + `action=CannonAttack/RangedAttack amount=10 subtype=MinimumRange relativity=Assign` + `action=FireAttack amount=1 ActionEnable`；目标单位需有 FireAttack protoaction（6.67 攻城/0-10/rof0.5/FireBallGreat/cap30，无 active 标记）+ 战术动作（stringid 122315，anim=FireAttack，active=0，throw/targetground/perfectaccuracy/basedamagecap）+ animfile 里的 FireAttack 动画（clip animation_library\building\ranged_attack，音效 set="FlameThrower"）。
- 建筑光环（科技启用建筑 AutoRangedModify 光环）：tactics 加动作 `<action><name stringid="103417">动作名</name><type>AutoRangedModify</type><active>0</active><maxrange>100</maxrange><modifyabstracttype>Building</modifyabstracttype><persistent>1</persistent><nostack>1</nostack><modifytype>BuildingWorkRate</modifytype><modifymultiplier>2.00</modifymultiplier></action>` 并注册进每条 tactic 的动作列表；科技加 `<effect type="Data" action="动作名" amount="1.00" subtype="ActionEnable" relativity="Absolute"><target type="ProtoUnit">单位</target></effect>`。modifymultiplier 为倍率（2.0=+100%）；Building 覆盖全部建筑（forbidunittype 可排除、modifyself 含自身、maxrange 可被科技 MaximumRange/Assign 改）；同类可用 modifytype：BuildRate/ResearchRate/FarmingGatherRate/MineGatherRate/TreeGatherRate/HealRate/InfluenceRate/MaxHP 等。原版范本：DEHCGobarauMinaret→deUniversity、HCXPNomadicExpansion→Teepee、DEHCVenetianArsenal→Arsenal、DEHCGreenwichTime→tradingpost。**光环图标（可见视觉）**=动作内加 `<modelattachment>effects\ypack_auras\econpower.xml</modelattachment>` + `<modelattachmentbone>bonethatdoesntexist</modelattachmentbone>`（原版经济光环浮动图标，castle/blockhouse/university/africantower 同款写法，动作随科技 ActionEnable 生效；其他备选图标见「Art/特效资源提取（.bar）速查」）。GEMOD 已实现：GELombardWorkRateAura（deLombard2，按钮页2列3，dbid 900096，字串 910256/910257，工业时代前置，2026-10 已加 econpower 光环图标+转储验证）。
- 新科技/新字符串：dbid 顺延（本工程 protomods 900001-900030 + techtreemods 900031-900084 已用；2026-10-10 水位 dbid 900104、字串 910281 → 下一个 900105 / 910282；单位 id 9957-9999 及 9956/9955/9954/9953 已占（9952/9951 已释放），下一个往下取 9952 或 9950）；displaynameid/rollovertextid 用自定段（910xxx 2026-10-09 水位 910267），字串写 Data\strings\<语言>\stringmods.xml（中英两份都写；en 文件新条目写英文）；新单位/新科技必须同时挂 Shadow 科技 ObtainableUnits（Enable）与 ObtainableUnitUpgradeTechs（TechStatus obtainable）。

## 自动生产/成本削减/军队换代 速查（2026-10 实战）

- **建筑自动生产单位（Maintain action，免费）**：tactics 加 `<action><name stringid="自定字串">动作名</name><type>Maintain</type><rate type="单位proto">1</rate><maintaintrainpoints>60.0000</maintaintrainpoints><active>0</active><persistent>1</persistent></action>` 并注册进该文件**所有 tactic 帧**的动作列表；科技用 `ActionEnable` 启用（`<effect type="Data" action="动作名" amount="1.00" subtype="ActionEnable" relativity="Absolute"><target type="ProtoUnit">建筑proto</target></effect>`）。语义：周期=maintaintrainpoints 训练点（≈秒；缺省=单位实训点×rate数量），**免费**、每周期产 rate 数量、persistent=1 无限循环（无 singleuse=1 时；有则一次性）、显示在训练队列。官方范本：DEHCFedTexanForts（原名句 "Forts now instead slowly train batches of units for free"）、DEHCFedWataugaAssociation、cossackstable（maintaintrainpoints=60）。**DE 里 Maintain 可直接产旗军**（老圣典"不能自动生产旗军"已过时）：被产军队按**生成它的建筑**在 civs/civmods 的 multipleblocktrain 注册展开（deTorp→deCaroleanBatch、FortFrontier→deFortStateMilitiaBatch 均如此），**无需 protoaction 占位**（FortFrontier 无 MaintainFedStateMilitia protoaction 仍工作）；动作名可自定义（同 GELombardWorkRateAura 先例），且 ActionEnable 的 action 名必须与动作定义名一致。
- **训练成本削减**：`<effect type="Data" amount="0.50" subtype="Cost" resource="Food" relativity="BasePercent"><target type="ProtoUnit">军队proto</target></effect>`；BasePercent=×(1+Σx%)（1.00=不变、0.50=五折、0.75=七五折）；每个资源类别一条；捆绑军队按其 proto 的 `<cost>` 计费生效。
- **捆绑军队升级换代（换装）**：新建变体军队 proto（同结构+新 id/dbid/字串）+ civmods 同建筑注册（同单位数）+ 建筑 `<Train>` 新列；变体**不进** Shadow ObtainableUnits（默认禁用）；科技 `Enable(+1)` 变体 + `Enable(-1)` 旧军队 → 研究后训练菜单即时换装（Enable 只控制菜单可见性，不影响已存在单位；旧军队的注册不用动）。
- 交付验证链：civmods 注册（建筑与自动生成建筑一致）+ 部署后引擎转储核验（techtreey/protoy/civs/strings/tactics 全部可 grep 到新实体；GESupportArtillery/GEModernSharpshooterArmy 即此法交付）。

## 自定义建筑继承基础科技效果（deHacienda2 镜像法）速查（2026-10 实战）

- 场景：自定义建筑 X2 复制了基础建筑 X 的全部机件（村民采集速率 type="X2"、战术/命令拷贝、影子科技 Enable），但基础科技效果仍只认 X——需要"对 X 生效的科技对 X2 生效"时，把效果**镜像为 X2 键名**（保持工程布线风格：一切按 X2 名字键控）。**不要**给 X2 加 X 的 unittype 别名：会连带触发限建/机件控制类 Assign 效果，且与既有 X2 键名速率条目匹配顺序不可控。
- 方法（已实战：155 科技/374 效果一次交付）：从 base techtreey 提取含 X 的 effect 块（target 内容 + 任意 attribute 值恰为 X），逐条生成镜像 effect：只把值**恰等于** X 的引用换成 X2（`="X"` 精确匹配；target 用 `>\s*X\s*<` 替换）——**禁止子串替换**（deHacienda→会误伤 deHaciendaWagon/deHaciendaSettler，用 NO-SUBST 检测兜底）；多 ProtoUnit target 的效果镜像只保留 X2 单 target（防重复叠加）；全部追加进 techtreemods：`<tech name="原科技"><effects><effect mergeMode="add" ...>`（改基础科技的合法写法，AoP 活例：YPAge0Japanese+YPAge0 系；小写 <tech>/<effects>/<effect> 亦可，CRLF→LF 需转换，文件保持 BOM+LF）。
- 甄别项：① 马车/命令名等子串引用跳过（非建筑本体）；② 休眠/控制类效果单独评估——如对"无法建造 X 的文明"的限建 Assign（Age0Spanish BuildLimit=2 对西班牙本就不生效），镜像到全文明可建的 X2 反而制造意外上限，应跳过；③ counttype / 命令 Add/Remove / TacticEnable / ActionEnable 均可镜像（base 同款结构；CommandAdd 到已含该命令的 proto 是 base 原生行为，不会重复按钮）；④ tactics 帧与 base 一致时 TacticEnable/ActionEnable 镜像全量生效。
- 验证链：转储 grep 每个科技块含 X2 + 计数比对（镜像数+既有条目）+ 相关训练行/按钮状态。
- GEMOD 现状（2026-10-09）：deHacienda2 = base 墨西哥庄园完整克隆（GESkirmisher 建造/全文明/限7/600木），村民采集速率、hacienda2.tactics（64 帧与 base 全对应）、命令均已按 deHacienda2 键名布线；科技效果镜像 155 科技/374 条已交付（SeedDrill/ArtificialFertilizer/Bookkeeping/Homesteading/OreRefining/SelectiveBreeding 及各文明卡片/原住民/革命科技）。

## 武器/模型替换（"某攻击使用X模型"）速查

- animfile 结构：顶层 `<attachment>名字<component>名字<assetreference type="GrannyModel"><file>模型路径</file>...` 定义挂点；**每个 `<anim>` 内联的 `<attach a="名字" frombone="武器侧骨骼" tobone="单位手骨" syncanims="0|1">` 决定该动画显示哪把武器**；组件级（ModelComp 内）的 attach 是"叠加"不是"覆盖"——若目标武器要取代原武器，必须删除 ModelComp 级同名 attach，或改为每个 anim 自带 attach（原版风格）。
- 实现"蓄力/特殊攻击使用指定模型"：① 新增 attachment（武器模型直接 inline 或 `<include>` 一个 *guns.xml）；② 复制原动画片段另起 `<anim>新动画名`（如 ChargeCarbine_attack/reload/idle、Attack_melee_charged 等），把 attach 指向新武器；③ tactics 里该 action 的 anim/reloadanim/idleanim 改为新动画名。武器骨骼对：手枪/卡宾 `frombone="MASTER"|bone_gun, tobone="BIP01 PROP1"`；长矛模型 units\mercenaries\elmeti\lance 用 `frombone="bone_sword"|bone_master, tobone="Bip01 Prop1"`。
- 常见模型路径：卡宾枪 units\cavalry\us_cavalry\us_cavalry_gun；装甲手枪兵手枪 units\generals\general_gun；教宗长矛骑兵长矛 units\mercenaries\elmeti\lance；火焰兵（deHoopThrower）火箭 = rocket_launcher 模型 + rocket.xml include；挂点参数 launcher: frombone="bone_gun" tobone="Bip01 Prop1" syncanims="1"，rocket: frombone="ATTACHPOINT" tobone="Bip01 Prop1" syncanims="1"，torch: ATTACHPOINT→L HAND；动画 animation_library\shared\rocket_idle/reload/attack（另 rocket_small_* 给火箭本体）；长枪冲锋/长矛动画 animation_library\cavalry\lance_*（idle_J/walk_b/gallop_b/charge_attack）；手枪动画 animation_library\SPC\cooper\{ranged_attack,reload,idle}。
- 骑马单位的每个动画必须在骑手与马两个 animfile 里同名定义（马侧用 horse_idle_A/canter/gallop 等等价 clip，通常不带 weapon attach），只改一侧会出现"人马不同步/骑手不动作"。
- 长矛冲锋（LanceChargeAttack）四层：protoaction（60/rof1.5/range4/cap120/area2/AbstractInfantry×1.5+active0+chargeaction1）+ 单位级 `<rechargetime>60`/`<chargeusagetime>0.25` + 骑手与战马 animfile 各加 Idle_charged/Walk_charged/Run_charged/Attack_melee_charged（骑手侧 attach 长矛，马侧仅动画）+ 专用 tactics（照 handCavalryShield.tactics：LanceChargeAttack 以 priority 30 加入全部地面战术）。
- 光环保卫（deShieldAura）：tactics 加 `<action><name stringid="122267">ShieldAura</name><type>AutoRangedModify</type><maxrange>12</maxrange><modifyabstracttype>AbstractCavalry</modifyabstracttype><persistent>1</persistent><modifytype>Shield</modifytype><modifymultiplier>0.30</modifymultiplier><modelattachment>effects\ypack_auras\papal_guard_power.xml</modelattachment><modelattachmentbone>bonethatdoesntexist</modelattachmentbone></action>`，各战术末尾加 `<action>ShieldAura</action>`，abilitymods 加 `<ability>deShieldAura<alwaysdisabledingrid>true</alwaysdisabledingrid><forceshowrollover>true</forceshowrollover></ability>`（modifymultiplier=吸收比例；同类单位目标有 AbstractCavalry/AbstractArtillery/LogicalTypeValidSharpshoot 等）。

## 步骑双形态（Mount/Dismount 按钮切换）速查

原版机制 = 两个独立单位 + `DelayedTransform` 动作互转（范本：deNatMountedInfantry↔Rider、deNatMercMountedInfantry↔Rider、deREVHaidamaka↔Rider）。**共 5 层，缺任何一层按钮都不出现或转换异常**：

| 层 | 改动 |
|---|---|
| ①单位对 | 两个 proto，各带 `<command page="11" column="0">Abilities</command>` + `<sharedselectionunittypes>` 互列对方 |
| ②各自主 tactics | 定义 `<action><name stringid="69148">DelayedTransform</name><type>DelayedTransform</type><anim>Mount（步侧）/Dismount（骑侧）</anim><animationrate>0.46875</animationrate><modifyprotoid>目标单位</modifyprotoid></action>`；**不**写入 tactic 动作列表（引擎自动出按钮） |
| ③单位级 protoaction | 再补 `<protoaction><name>DelayedTransform</name><modifyprotoid>目标</modifyprotoid></protoaction>`（共享 tactics 时引擎以单位级为准） |
| ④**技能层（易漏！）** | `Data\abilities\abilitymods.xml` 加单位块：步侧 `<ability>dePowerMount<rof>1</rof><castonself>true</castonself><forceshowrollover>true</forceshowrollover></ability>`、骑侧 dePowerDismount；晋升展示加 `dePromotionRangeSPD`/`dePromotionHpDMG` 等（对应 veterancybonus 类型）。**按钮本体由此生成，只写 tactics/protoaction 不会出现按钮**（dePowerMount/dePowerDismount 本身在 powers.xml 已定义，只引用不重定义） |
| ⑤启用 | 两个 proto 都要进 Shadow 科技 ObtainableUnits 的 Enable 列表 |

- **过渡动画必须叫 Mount/Dismount 且真实存在**：原版全部 mount 对的两个 animfile（骑手侧也算）100% 定义了同名 anim（步侧 mount→animation_library\cavalry\horse_mount/human_mount_horse；骑侧 Dismount→horse_dismount/rider_dismount），DelayedTransform 的 `<anim>` 也一律写 Mount/Dismount——不要图省事改成模型自带的 Limber/Idle 片段（会埋坑）。自定义模型也给自己的 animfile 加这两个 anim 名（映射到自身存在的片段，如加特林机枪 Mount→limber 片段、加特林骆驼 Dismount→camel idle）。
- 骑手侧 animfile（含 mod 覆盖版）也要能响应 Dismount，否则转换期间骑手不动作（可给人形骑手加 `<anim>Dismount<file>animation_library\cavalry\rider_dismount</file>`）。
- 晋升（"Benefits from promotions"）= 单位级 `<veterancybonus>`：rank0/1/2 各 `<veterancymodify modifytype="RangeAbsolute">1/2/3.0</veterancymodify>` + `<veterancymodify modifytype="Speed">1.05/1.10/1.15</veterancymodify>`（原版仅骑马步兵族同时给射程+速度）。
- 骑乘者模型替换：改主（马/骆驼）模型文件的 `<attachment>rider<include>新骑乘者.xml</include>` + `<attach a="rider" frombone="骑乘者自身挂骨" tobone="宿主挂点骨">`。宿主挂点骨看宿主现有 attach（马=Attachpoint、加特林骆驼=bone_attachpoint）；骑乘者挂骨抄该骑乘者**原配 horse 文件**里的 frombone（标准骑手=hotspot，骑马步兵=Bip01_Root，加特林骑手=bip01_root）。
- 交付前无法进游戏看模型时：把不确定的 attach 骨名、转换动画写在报告里让用户实测反馈。

## 弹药与特效速查（火焰灼烧/榴霰弹等）

- 火焰灼烧（命中者燃烧）= 战术动作里加 `<attachprotounit>DEBurningAttachment</attachprotounit>`（lifespan 10s；范本 tactics/archer.tactics RangedBuildingAttack，配合 `<projectile>ArrowFlaming</projectile>` 或 ypFlamingArrowAmmo）。
- 火焰之箭弹药 = `ypFlamingArrowAmmo`（中文名即"火焰之箭弹药"，中国火焰之箭炮的弹）；燃烧箭 = `ArrowFlaming`；命中特效 effects\impacts\torch。
- 榴霰弹 = Case Shot（napoleongun/leathercannon 的 CaseShotAttack，stringid 91718/91723）；原版是 InvisibleProjectile+gun 冲击；要可见爆炸用 `<projectile>CannonballSmall</projectile>` + `<impacteffect>effects\impacts\cannon</impacteffect>` + damagearea。
- 可用 impacteffect 枚举：melee/gun/torch/cannon/mortar/arrow/dynamite/chakram 等（对 tactics 目录统计得到）。

## 随机地图（RandMaps）与运行期触发速查

- **对局失败的快速诊断**：CXSDump（`RandMaps\Age3DERM<图名>.dmp.txt`）和 `Trigger\trigtemp.xs` 是每次生成都会写的正常产物（不是崩溃日志）；dump 头 `Code: N bytes (MAX=2^k)` 自动翻倍（32K→64K→…→524288），`Rules: 0` = 快照在规则注册前，别误读。map 的 trigtemp.xs 能看到触发器编译结果（rule 名=下划线+触发器名，效果展开为 tr* 调用）。判断“对局到底开没开”：看 `Logs\Age3Log.txt`——正常开局在 preload 后日志格式切换为帧/时间前缀；若 preload 后直接进 `mode 52 (OutsideGameHomeCity)` 且仍用 `PreGame <ms>` 前缀 = 对局没开始（会回主城）。
- **保守 API 集（base 兼容验证过的）**：`Timer` 条件 + `Grant Resources`（ResName 必须大写 “Food/Wood/Gold/Ships”！小写是隐患）+ `Unit Create from Source Multi` + `Send Chat`(PlayerID 0) + `Set Tech Status`(rmGetTechID) + `Modify Protounit`；**不要用 `Counter:*`/`Fire Event`**（仅自带 triggerdata 的 AoP 用过），长周期用「静态一次性 Timer 链」；循环不要依赖 Loop(true)。
- 每个玩家必须有开局 TC（哪怕什么都不做），否则对局可能开不起来或瞬败；地图加标准 include（mercenaries.xs / ypAsianInclude.xs / ypKOTHInclude.xs）；cos/sin/rmEchoError 可用。

- 自定义随机地图 = mod 根目录下一对文件：`randmaps\<名>.xs`（脚本）+ `randmaps\<名>.xml`（mapinfo，直接放 mod 根 randmaps\ 即被游戏加载，不需注册/XMB）。
- 地图图片：mod 根 `data\wpfg\resources\images\icons\random_map\<x>\logo.png` \<-> xml 里 `imagepath="ui\random_map\<x>\logo"`；loadss 用 `resources\images\icons\random_map\<x>\ss_0N` 形式；mapinfo 模板参照生存图集（detailsText/displayName 可直接内联文本+`\n`，中文 UTF-8）。
- **运行期逻辑用 rm-触发器系统**（生存图集/AoP 大量使用，纯地图文件无需改数据）：`rmCreateTrigger(名)` + `rmSwitchToTrigger(rmTriggerID(名))` + `rmSetTriggerPriority/Active/RunImmediately/Loop`，条件 `rmAddTriggerCondition("Timer")` → `rmSetTriggerConditionParamInt("Param1", 秒, false)`；效果 `rmAddTriggerEffect(名)` + `rmSetTriggerEffectParam(Int/Float)`。
- 已验证效果名：`Timer`/`Units in Area`/`Difficulty Level` 等条件；`Grant Resources`(trPlayerGrantResources)、`Unit Create from Source Multi`(SrcObject=目标对象、PlayerID=归属、Count/Heading 用字符串参数)、`Send Chat`(PlayerID 0=系统)、`Fire Event`、`Counter:Add Timer`+`Counter Visible false`（隐藏计数器可当节拍器循环触发）、`Set Tech Status`(rmGetTechID)、`Move To Point`/`Unit Work`/`AI Create Attack Plan`。效果完整定义可读 AoP mod 的 `data/trigger/triggerdata.xml`（stock+ZP 扩展，ZP 前缀才是它的自定义）。
- 对象引用：`rmPlaceObjectDefAtLoc(def,玩家,x,z)` 后 `rmGetUnitPlacedOfPlayer(def,玩家)` 取单位 id（一 def 一单位），可直接当 SrcObject/DstObject 的 ParamInt 用；main() 生成期可用 `if(f1>0){...}` 动态决定是否加触发器效果。
- **军团容器与参数值规范（"一队单位"类效果通用，见「传送/瞬移」速查）**：`rmCreateArmy(玩家,名)`→整型句柄；Army 系效果（Army Deploy / Army Change Type / Army Teleport…）用 `rmSetTriggerEffectParamArmy("SrcArmy", 玩家, 句柄)` 传军团（活例：生存图集 jaileight.xs 1547 起、crate battle.xs 的 ArmyDeploy 封装）。参数按 vartype 传值：unit→`rmSetTriggerEffectParamInt("SrcObject", 单位ID)`（先例 Convert / Unit Create from Source Multi）；area→米制逗号串 `rmXFractionToMeters(x)+", 0, "+rmZFractionToMeters(z)`（先例：Army Deploy 的 Location）。
- **敌人进攻靠 AI**：生成单位归电脑玩家即可，标准 AI 会自动出兵（71 张生存图集无一写真性攻击指令）；不要给敌方玩家开局资源/TC（否则 AI 提前自训）。
- 触发循环限制：Loop(true)+Timer 语义未充分验证；长周期性用「静态一次性触发链 + 隐藏计数器 ping-pong（Counter:Add Timer→Event=另一触发器）」最稳。
- 语法坑：for 用 `for(i=1; <= N)` 方言或完整 C 式均可；给所有单语句 if/while 加花括号最稳；`.xs` 用 CRLF+无 BOM；字符串限 ASCII。
- 失败排查：地图加载失败会写 `<USER_HOME>\Games\Age of Empires 3 DE\<id>\RandMaps\Age3DERM*.dmp.txt`（CXSDump）——读它定位脚本错误。
- 现成参考：mods\subscribed\314231_survival maps collection（71 张生存图，rm 触发器大全）、mods\local\42687_age of pirates\randmaps（战争/城市地图）。GEMOD 自己的地图：randmaps\gefortsiege.xs（无限资源+堡垒波次），生成器 workSpace\tools\gen_fortsiege_map.py。

## 传送/瞬移（Teleport）速查（2026-10 盘点）

"让一队单位从 A 传到 B"只有两条真实路径；**没有**普通单位"技能按钮式传送"的现成数据件（protoy/tactics/abilities 全库扫描 0 命中，别往单位动作方向做）。机制盘点通用法：① triggerData.xml 搜现成触发效果 ② exe 静态字符串扫描（类型表/RTTI 类名/parseNode 报错串，法见 references/exe-reverse-engineering.md「轻量第一步」）③ sourceData 非 strings 全扫描现数据引用量（0 引用=引擎支持但未启用）。

**路径 1：触发器层（推荐，最稳）**——triggerData.xml 内置效果，场景编辑器零代码可用：
- "Teleport Units"（行 628：源单位列表+Area）、"Army Teleport"（行 914：军团+Area）、"Teleport to Unit"（行 1836：源单位→目标单位）；底层 `trUnitTeleport`（把"选中单位"瞬移到坐标）/`trUnitTeleportToUnit`（瞬移到目标单位处）。
- "Move From Area"（命令行 1383，trUnitMoveFromArea）：按 玩家+类型+半径 批量移动——**是移动不是瞬移**，但能动态圈任意单位（teleport 族只作用于已知引用/军团），"整片区域搬走"用它。
- RM 地图：一队=军团容器 → "Army Deploy" 登记到 A、"Army Teleport" 整队到 B；单单位用 "Teleport to Unit"+`rmSetTriggerEffectParamInt("SrcObject"/"DstObject", 单位ID)`（军团容器与参数值规范见上节「随机地图」速查）。RM 接受 triggerdata 注册表内全部效果名（Army Deploy/Change Type 已被生存图集 RM 实跑）。
- 待实测（写代码时预留）：Area 字符串格式、传送落地行为（聚拢/散布、命令队列是否清空）——只能进图观测，转储核不到。

**路径 2：Power 层（任意对局可用，实验性）**——引擎注册 `BProtoPowerTeleport`/`AVBPowerTeleport`，类型枚举含 `Teleport`，解析节点 `InPortal`/`OutPortal`（单位引用）+`InEffect`/`OutEffect`；但现数据 0 引用（powers.xml 241 个 power 无实例）、语义无文档 → 要做就搭最小实验包，别当现成件用（失败模式未知）。
- 接线五件套（照 deMarchRevolution 活例）：powermods.xml（`<power name=… type=…>` 行为定义）→ protounitcommandmods.xml（`<associatedpower>`+`<castpower>`，DBID 必填）→ protomods `<command page=… column=…>` → abilitymods.xml（`<单位名小写><ability>技能名<rof>…<tech>门控<usebigabilitybutton3>`）→ 科技+字串。现例：`<towncenter>` 挂 deMarchRevolution、`<dehousedanish>` 挂 deScanianResistance；ch18 手册：AssociatedPower=共享冷却、CastPower=命令施放。
- 同类现成件（不用传送时的替代）：SwapUnit（临时换兵种）、EscapeToTC（撤回主城，圣典 9-9 模板可直接搬）——"回城/召回"需求不需要传送。
- 配套：animtypes.xml 有 TeleportIn/TeleportOut 动画类型（演出用；单位 animfile 是否含该动画未验证）；hcUnitTeleportToWPID 仅主城界面；AI 侧 cAttackPlanTeleportLocation=20+AutoUseGPs=21/PowerID=22（战役级通道，未验证）。

## 领事馆/使馆盟友系统（盟友军队+结盟科技）速查

- **DE 关键机制：protounit 默认处于"禁用"状态**，由各文明 Age0 科技逐项启用（例：Age0British 会 Enable Musketeer；NativeEmbassy 由 Enabler 启用）。Enable(+1/-1) 只控制训练菜单/科技按钮可见性，**不影响**卡牌/科技/旗帜军队生成的单位（证据：英国火器卡给埃塞送 deMercHarquebusier，该单位对埃塞并未 Enable）。
- MOD 新单位/建筑要可见：挂 Shadow 科技 ObtainableUnits/ObtainableBuildings（Enable），并把 Shadow 激活补进**每个文明**的 Age0 科技：`<Tech name='Age0French'><Effects><effect mergeMode="add" type="TechStatus" status="active">ObtainableUnits</effect>...`（GEMOD 已覆盖 30 个文明；SPCRenoGang/SPCHoleGang/SPCSomalis 等战役文明无 Age0 链，不覆盖）。
- **旗帜军队/批次单位**（"X雇佣连"一类）：proto = `<unittype>AbstractBannerArmy</unittype>` + `<idletimeout>5.0</idletimeout>` + tactics bannerman bannerArmy.tactics + AllowOverPopCap；**编成写在 civmods/civs.xml 的 `<multipleblocktrain>`（building+multipleblockunit+units/unitcounts），必须每个文明单独登记**；按钮 = 建筑 proto 的 `<train row=…>` 行；可见性 = 军队单位的 Enable 状态（默认禁用→由结盟科技启用）。
- **结盟互斥**（一次一家、切换自动解除）：结盟科技 effects = Enable 己方军队×3 + `<effect type="TechStatus" status="obtainable">` 盟友科技 + 对另一家 `amount="-1.00"` Enable/ unobtainable；科技自身 `<status>OBTAINABLE</status>` + `<flag>YPInfiniteTech</flag>`（保持可重复点击=可换回）。原版另有 ypBigSequesterX（`<sequestertech>` 关联）做"解除关系"流程。
- **强制全开原版升级链**：`<effect type="TechStatus" status="active">升级科技名</effect>`。埃塞：DEEliteInfantryEthiopian / DEEliteNeftenyaShadow（内夫特尼亚专属+15%）/ DEChampionInfantryEthiopian / DELegendaryInfantryEthiopian / DEIndustrialSebastopol / DEImperialSebastopol。印度：YPDisciplined/Honored/Exalted+Sepoy、CamelGun（=AbstractZamburak，含 Mansabdar）、Howdah、Mahout、YPHonored/YPExalted+SiegeElephant；Howdah/Mahout 的 Disciplined 层用 ypDisciplinedHowdahShadow / ypDisciplinedMahoutShadow；**Sowar 的 Camel 家族（AbstractSowar）≠ Zamburak 的 CamelGun 家族**。
- **科技送单位**：`<effect type="Data" amount="8.00" subtype="FreeHomeCityUnit" unittype="deZebuCattle"><target type="Player">`（范本 NativeTreaty*，送到主城集结点）；"不消耗船运次数"= 只写 Food/Gold 成本 + YPInfiniteTech，不写 Ships 成本。
- GEMOD 现成设施（可直接挂靠）：**GEConsulate**（id 9968，dbid 900067，原住民使馆模型，200木/3000HP/限1，GESkirmisher P6C7 建造，ObtainableBuildings）；盟友科技 GEAllianceEthiopia/GEAllianceIndia → 6 支军队 GEEthiopiaArmy1-3/GEIndiaArmy1-3 + 10 项科技（GEShipZebu/GEChewaElites/GEFirearmsBritish/GELegendaryEthiopia/GEShipPets/GEElephantArmors/GEIndianGunpowder/GELegendaryIndia）；字串 910186-910226。
- **GEConsulate 三盟友现状（2026-09 扩展后）**：新增 `GEAllianceNordic`（结盟北欧）→ 4 支军队 `GENordicArmy1-4`（Minuteman+GEWatchHouseWagon／deCarolean+deFinnishRider／deCarolean+deLeatherCannon／deREVSerdyuk+deREVStarshyna+deREVCossackTabor）+ 5 项科技 GEDanishSpecialty/GEDanishGuard/GESwedishGuard/GESwedishLegend/GEAgeOfChaos；三盟友互斥由各结盟科技互相 `-1 Enable`+`unobtainable` 实现，解约 GEBreakAlliance 统一复位。ID 水位（2026-10-10）：单位 id 已用至 9953（9952/9951 释放）、dbid 至 900104（跨 protomods+techtreemods 全局唯一）、字串至 910281；下一个 9952 / 900105 / 910282。**civmods 只有 31 个可用文明注册（XPAztec/XPSioux/XPIroquois/Indians/Pirate/SPC 系列无 GEConsulate 条目）**，新军队沿用同覆盖范围即可。
- **丹麦/波兰（DLC）资源映射（做北欧/东欧内容必备）**：自由枪手 Friskytter = 原型 `Minuteman`（由 `RGFriskytter` SetName 改名 130223）；瞭望屋 = `deHouseDanish`（displaynameid 130926，P0C0 训练 Minuteman）；海关 = `deCustomsHouse`；海关马车 = `deCustomsHouseWagon`（唯一在 civs.xml 以 townstartingunit 发放，非卡片）；圆堂 = `deChurchDanish`；安全屋卡 = `DEHCAdvancedHousesDanish`；赫尔辛格海关卡 = `DEHCAdvancedCustomsHouse`；瞭望屋科技 = DEHouseDisruption/DEHouseZealandJaegers/DEHouseRoyalService；海关科技 = DETollRegister/DECargoInspections/DEBorsen/DESoundBlockade/DEShipmentDelay/DEKalmarFleet；斯图亚特单位 = deNatClansman/deNatLowlanderInfantry/deNatLowlanderRider/deNatBagpiper（玩家版 = deNatMerc*），升级 = DEVeteranStuart/DEGuardStuart；谢尔久克/哥萨克军官/战车 = deREVSerdyuk/deREVStarshyna/deREVCossackTabor；瑞典 = deCarolean/deFinnishRider/deLeatherCannon（升级 VeteranCaroleans/GuardCaroleans/ImperialCaroleans、VeteranFinnishRiders/GuardFinnishRiders/ImperialDrabants、deInfantryGuns/deImperialInfantryGuns；轮射=DEHCPlatoonFire、弹簧枪机=DEHCSnaplocks、斯韦亚卫队=DEHCSveaLifeguard）。原版**没有**瞭望屋马车，需自建（复制 deCustomsHouseWagon，改 `<train>`+Build rate 目标建筑、displaynameid/icon/animfile 即可）。
- **`allowedage` 语义**：0/1/2/3 = 时代 I/II/III/IV（Musketeer=1、Skirmisher=2 佐证）；banner 军队的 `<allowedage>` 即训练按钮的时代门槛，展开的子单位不受其自身 allowedage 限制。
- 脚本陷阱：往 techtreemods 追加新盟友科技时，若新科技复制了既有盟友的 effect 列表，`<effect ... unobtainable>GELegendaryIndia</effect>` 等尾部文本会重复出现——**替换锚点必须带上 SetCivRelation 的 `civ="DEEthiopians"`/`civ="Indians"` 上下文行**，否则 replace 命中新科技或替换错对象。
- 陷阱：新插入 XML 的换行必须与目标文件一致（不要凭经验；改前逐文件实测 BOM/换行——2026-10 实测：protomods/techtreemods=BOM+LF，strings=无BOM+LF，自定义 .tactics=无BOM+CRLF；行尾自检：CRLF 文件 loneLF 应为 0、LF 文件 CR 计数应为 0）；写完自检 `loneLF = bytes.count(b'\n') - bytes.count(b'\r\n')` 应为 0；git 的 "CRLF will be replaced by LF" 警告是 autocrlf 归一化，可忽略。替换 `</根节点>` 时注意原文件的 `\t` 缩进会留在插入点前，需手动修正。

- **大按钮与盟友介绍（关键）**：领事馆盟友大按钮**不在建筑 protoy 行里**，而是由 `politiciandata.xml → politicianmods.xml`（根 `<politicianmods>`）按**技术名小写**提供头像渲染：`<技术名小写 portraitfilename="ui\ingame\politicians\xxx" portraitfilenamewpf="resources/images/icons/politicians/xxx.png">`（原版 ypBigConsulate* 全库无 train/tech 行；GEMOD 已建 `Data\politicianmods.xml`：geallianceethiopia/geallianceindia）。配合技术旗标 YPUseBigButton3+YPConsulateTech（DE 里盟友大按钮渲染主要靠 politicianmods+YPConsulateTech；部分老盟友带 BigButton2/3 属历史残留）；YPUseBigHugeButton=单个超大按钮（ypPickConsulateTech "开放关系"，建筑 P18C0）。头像可复用游戏内任意 wpf 图片路径（如 politician_ethiopian_queen.png、consulate_india.png、allegiance_*.png）；自定义 PNG 放 `<mod>/data/wpfg/resources/images/icons/politicians/`。盟友介绍=大按钮 rollover，用原版格式 `奖励：…\n\n训练：…\n\n船运：…`（DE 自动展示 Advanced Rollover）。
- **盟友选择/介绍弹窗的真正机制（最重要）**：DE 的领事馆结盟交互 = **`uiconsulatedlg` 弹窗**（数据文件 `Data/uiconsulatedlg.xml`，内部 gadget 名 PoliticianDlg；AoP 的 `wpfg/uipoliticiandlg.xaml` 里注释 "Politician Container for EUROPEANS, NATIVE AND CONSULATE" 证实领事馆与政治家共用弹窗体系），弹窗以大肖像卡片形式列出可结盟盟友（即盟友介绍+大按钮）。**弹窗由原版 `ypPickConsulateTech` 网关按钮触发**（YPUseBigHugeButton；AoP 全程路由经由 ypPickConsulateTech——其自定义盟友效果里写 `TechStatus obtainable ypPickConsulateTech`）。自定义建筑接驳完整清单：① 建筑加 `<unittype>AbstractConsulate</unittype>`；② 建筑行注册 `<tech row="0" page="18" column="0">ypPickConsulateTech</tech>` 并由 shadow 使其对全文明 obtainable；③ 盟友科技加 YPConsulateTech+YPUseBigButton3+YPSequesterTech 旗标 + `<sequestertech>` + SetCivRelation（civ=内部文明名如 DEEthiopians/Indians，解约时 civ="none"）；④ politicianmods.xml 头像条目；⑤ 解约科技效果里重新 `ypPickConsulateTech obtainable`。盟友科技**原版不写建筑行**（由弹窗呈现）；补行=兼容保险（弹窗未验证前保留）。
- **解约（解除盟约）体系**：解约科技= `NativeDance`+`YPInfiniteTech`+`YPSequesterTech` 旗标 + icon `politicians\consulate_endrelations.png` + `<icontexturecoords>.001953125 .001953125 .7890625 .6015625</icontexturecoords>`；盟友科技上加 `<sequestertech>解约科技</sequestertech>` 与 `YPSequesterTech`。原版解约效果= -1 Enable 军队×3 + 盟友科技 unobtainable + `ypPickConsulateTech obtainable`。TAD 已知缺陷：解约后盟友按钮不回来（只能解约1次；圣典方案=造 N 套盟友/解约科技对）；**GEMOD 方案=结盟按钮被研究后自我隐藏+同时隐藏另一家与 ypPickConsulateTech；解除盟约时全部重新 obtainable（已研究过的科技再设 obtainable 按钮会重现，原版网关自隐→重现循环已证）→ 无限次换盟友且按钮状态与原版一致（结盟后只剩解除盟约）。**
- 建筑要让引擎当领事馆处理：补 `<unittype>AbstractConsulate</unittype>`（全库无技术引用它，安全；GEConsulate 已加）。
- 陷阱：Python 文本模式读取这些 XML 会 universal-newline 把 CRLF 折成 LF，导致带 `\r\n` 的锚点失配——**一律用 bytes 读写**。
- 陷阱：terminal heredoc 传反斜杠字面量不可靠（实测会把路径中的 反斜杠+a 折叠误转义成 BEL 字节，毁掉 icon 路径）——含反斜杠内容（路径/转义）改用 execute_code 字节替换、或 Python 内 bytes([92]) 拼接构造，写后对关键行做字节等值验证。

## 自定义 AI（让电脑使用模组内容）速查

- DE 的 AI 脚本位于 `游戏安装\Game\AI\`：入口 `aiLoaderStandard.xs`（include aiHeader+aiMain），核心 `core\*.xs`（规则=rule 块+xsEnableRule），性格=`personalities\*.personality`（`<script>aiLoaderStandard</script>`）+ `personalities.xml`。
- 模组挂载 AI：`<mod>\Game\AI\...`（AoP/Enhanced AI/怪物文明三例实证）。**AI 脚本必须覆盖某个默认脚本才会被加载**——最小侵入 = 只覆盖 `aiLoaderStandard.xs`（原版逐字保留 + 加 include 新文件 + postInit 调 init），全部逻辑放新增文件；规则统一加前缀（如 gemod）防冲突。
- 关键函数：`kbGetProtoUnitID("名字")`（名→ID 运行时探测，无效<1）；`kbProtoUnitAvailable/CanTrain/IsType`；`kbTechGetStatus`（cTechStatusObtainable/Active）；`kbTechTreeGetCheapestUnitUpgrade(puid,训练建筑puid)`（自动发现单位升级科技→新升级免维护）；`kbCanAffordTech(tech,escrow)`；`kbResourceGet(cResourceShips)` 查船运；`aiTaskUnitTrain/aiTaskUnitResearch(建筑单位ID,…)` 直接下任务；`findWagonToBuild(puid)` 返回可建该建筑的马车 PUID；`getUnit(puid)` 取活体 ID；`xsGetTime()` 秒；`aiChat(1,"…")` 开局横幅（验证加载）。
- `cUnitType*`/`cTech*` 常量由 AI 编译器**按名解析**（任意内容含模组内容；AoP 的 cTechzp* 实证）；无枚举 API → 未来新增内容需按名注册进 AI 文件。
- 训练：`cPlanTrain` 计划（cTrainPlanUnitType+cTrainPlanNumberToMaintain，自动找训练建筑）；军团包/军队 = `aiTaskUnitTrain(建筑ID,包单位)`（包会 idletimeout 自动展开）。建造：`cPlanBuild`+`cBuildPlanBuildingTypeID`+`selectBuildPlanPosition(plan,puid,baseID)`（未知 puid 走 default 分支正常）+ **显式 `aiPlanAddUnitType(plan,建造者PUID,1,1,1)`**。陷阱：`createSimpleBuildPlan/addBuilderToPlan` 对自定义建筑只会塞 gEconUnit（普通村民）且不校验其能否建造——模组建筑必须自己指定建造者（专属工兵/马车/wagon 用 findWagonToBuild 取）。
- DE AI 无附加式机制：整包 AI 模组互相排斥（同文件只能生效一份）；`personalities.xml→personalitiesmods.xml` 是唯一附加式 AI 相关文件。
- **XS 语法硬性约束**：函数参数必须带默认值（参数写法=变量定义且必须有初值，否则编译报错「需要初始化变量」；原版 414 个函数定义 100% 带默认值，字符串可用 `= ""`，先例 debugUtilities）；`xsGetTime()` 返回 **int 毫秒**（原版用 `10*60*1000` 换算分钟），节流计时用毫秒整数而非 float 秒。
- **跨模组 AI 混装（重要）**：同名 AI 文件按路径跨模组逐文件决出（实测本地 GEMOD pri3 压过订阅 Enhanced AI pri23）；Enhanced AI 是唯一自带旧版 `aiHeader.xs` 的整包 AI 模组（AoP/怪物文明都复用 DE 基础头部），其头部缺 DE 新增变量 cvOkToTrainOutlawsAndMercenaries、cvOkToTrainArtillery（btRushBoom/btOffenseDefense/cvOkToAttack/cvOkToTrainArmy/cvOkToTrainNavy/cvOkToAllyNatives 存在）。混装时（他模组加载器/头部+你的文件）加载器与自定义文件**不得引用旧头部缺失的 DE 新增符号**；引擎级 kb*/ai*/xs* 函数与常量不受影响（引擎始终为当前版本，仅脚本层被替换）。排查：Age3Log.txt 搜 `AI ERROR`/`XS: Error`（带文件名+行号）。
- GEMOD 现成实现：`workSpace/GEMOD/Game/AI/{aiLoaderStandard.xs, gemodai.xs}`（7 规则：建造/工兵/军备/军团包/领事馆/科技/升级）；说明 `docs\GEMOD_AI模块说明.md`。

## 英雄皮肤/英雄自定义 速查

- 游戏内"英雄皮肤"（主城/大厅给英雄选皮肤：默认/女性探险家/Ada Lovelace/Warwick/Drake/Arctic…）**只对原版各文明原生英雄 proto 生效**：欧洲系=Explorer；其他=xpAztecWarchief/xpIroquoisWarChief/xpLakotaWarchief/deIncaWarChief/ypMonkChinese/ypMonkIndian/ypMonkJapanese/deGeneral/deGeneral2/dePadre/deEmir/dePrince/deRegent/deGrandMaster/deHetman（`homecity<Civ>.xml` 的 `<heroprotounits>` 就是这张清单；墨西哥 2 个）。
- 皮肤三件套的落点：**语音=数据层**（`Sound\<英雄proto>_snds.xml` 的 `<skinlogic>` 按 skin id 选音效集，音效集定义在 soundsets*.xml）；**图标/头像=数据层**（Age0<Civ> 科技里 `<effect type="Data2" subtype="CopyUnitPortraitAndIcon" unittype="英雄proto" skinid="N">` → target=deIcon* 单位；protoy 另有带 id 参数的 SkinIcon/SkinPortrait 属性）；**模型=客户端侧、数据层无落点**（warwick.xml、female\lovelace\lovelace.xml、o_explorer\sahin.xml 等皮肤 animfile 在全解包数据+exe（含 UTF-16 检索）中 0 引用；走 exe 符号 ExplorerSkinChange/SkinFilePath 流程）。
- 因此：**自定义新单位（如 Explorer2）无法通过数据获得皮肤模型**（补 `<unittype>Hero</unittype>`/`<flag>HeroName2</flag>` 也没用）；要让"玩家所选皮肤+其附带语音"生效，必须让出场单位=该文明原生英雄 proto（对该英雄做 protomods modify），不要新建英雄单位。保留自定义单位时就只能固定外观；皮肤图标/头像可照 CopyUnitPortraitAndIcon 补，语音 skinlogic 是否命中须游戏内实测。
- 换名/换像类效果末尾加 `<effect type="Data" subtype="UpdateVisual" unittype="单位"><target type="Player">`（原版 589 处，SetName/CopyUnitPortraitAndIcon 之后刷新已存在单位显示）。
- 明细（英雄清单/图标写法/皮肤模型路径/选择存储位置/判定"能否数据实现"的排查方法/实现路线）：references/hero-skins.md。

## 动物吸引/跟随（磁铁机制）速查

"移动单位吸引动物→动物跟随"=引擎原生两层机制；官方移动单位样板=萨米诺伊迪（科技 `DENatSamiReindeerHerding`）：

- **吸引层（磁铁）**：目标单位挂 `<unittype>AbstractTypeHerdableMagnet</unittype>`（吸牲畜：herd.tactics 的 19 种——羊/牛/骆马/山羊/牦牛/猪/鹅/非洲牛等）和/或 `<unittype>AbstractTypeHuntableMagnet</unittype>`（吸猎物：hunt.tactics 的 30 种——鹿/野牛/驯鹿/野羊等；`Huntable` 是字面 unittype）。原版静态用例：Farm/村庄/圣田/神社/东照宫/牲畜市场/大庄园/福尔瓦克畜栏=牲畜磁铁，deGranary=猎物磁铁；革命卡 DEHCREVMXBajaCaliforniaTerritory 用 `SetUnitType` 给 deHacienda 运行时加猎物磁铁。
- **跟随层（采集合约）**：动物须有 Gather 动作含 `<rate type="目标单位名">`（样板 hunt.tactics 的 NoaidiGather：`<type>Gather</type><maxrange>1</maxrange><donotdepositresources>1</donotdepositresources><rate type="deNatNoaidi">1.0</rate>`）。动物走到目标旁"采集"它（无产出），目标走远→超距重寻路=跟随。**双层结构（2026-09 GEMOD 实测校正）**：跟随合约必须落在动物身上两层——① 共享 tactics 的 Gather 动作（含 `<rate type="单位名">`）；② 该动物自己的同名 `<protoaction><name>…</name><active>0</active></protoaction>` 占位（官方唯一移动磁铁 deNatSamiReindeer 即此结构；`<active>0</active>` 占位不阻断运行，先例 deSPCCommandPost AutoConvert：proto 占位 0 + tactics 动作活 = 功能正常）。**只挂单位侧（磁铁+flags，或借 AbstractShrine 冒充神社的便桥）实测均不触发吸引——便桥方案已废弃。**
- **移动磁铁必备 flag**（萨米三件套）：`<flag>MagnetDoesNotLockUnits</flag>`（被吸引动物不锁死；deHacienda/deGranary 原生带）+ `<flag>AllowGatheringWhenFull</flag>`（不产资源目标可持续被采集；原生仅 deHacienda+萨米科技）+ 磁铁 unittype。`UseAnimalsLabel` 原版三处（ypSacredField/ypShrineJapanese/deGranary）均为磁铁建筑，可一并加。
- **门控写法**（科技运行时追加，relativity=Assign）：`subtype="SetUnitType" unittype="AbstractTypeHuntableMagnet"` + `subtype="ProtoUnitFlag" flagname="MagnetDoesNotLockUnits"|flagname="AllowGatheringWhenFull"`，target=ProtoUnit。
- **共享 tactics 改法**：herd.tactics/hunt.tactics 整文件覆盖式（CRLF 无 BOM）；要专属跟随动作=完整复制原文件+加动作+挂进每条 tactic 的动作列表；只需部分动物跟随=复制成 <动物名>.tactics 再改该动物 proto 的 `<tactics>` 指针。
- **≠跟随的相邻机制**：`AutoConvert`（herd.tactics 内置 maxrange 12，字符串 69161"自动招降"=归属切换）；`ConvertsHerds`（全库绝大部分单位/建筑都有——不是吸引标记，别当跟随依据）；`ConvertGuardian/RecruitGuardian`（16 范围收服宝藏守护者）。
- 未定项（只能游戏内实测）：移动中是否持续吸引（官方文案只承诺"空闲或采集时吸引野生动物"，130662）；吸引半径；已归属动物是否响应；lock 语义；速度账（羊 4.0/6.0，轻骑侦察兵 6.75/8.5 会甩开动物，诺伊迪 4.0 与动物同速）。
- GEMOD 现状：ypScoutHerder（id 9971，deLombard2 训练）已挂双磁铁+ConvertsHerds+UseAnimalsLabel+MagnetDoesNotLockUnits+AllowGatheringWhenFull（AbstractShrine 便桥已注释—实测无效）；动物侧 ScoutHerderGather 双层已全量铺设（herd/hunt.tactics 覆盖版：动作+注册；protomods：49 动物占位）；同库建筑侧磁铁：deTorp2（id 9986，双磁铁+AbstractShrine+UseAnimalsLabel，未加"不锁定"）与 deHacienda2（含二 flag）；字节编辑注意 UseAnimalsLabel 等串在文件中多处出现，锚点必须带上下文；文案 910106=「能够吸引野生动物并使其跟随移动的骑兵侦察兵」。- **排查技术栈（2026-09 实战沉淀）**：磁铁/双层合约全部就位仍零反应时，问题在引擎**靶侧准入条件**；用「多假设变体包」（同一建筑并列 5~6 个只差单一变量的实验单位，一次游戏测完）比逐轮猜测快一个数量级。
- **取证工具箱**：① DebugOutputGameData：user.cfg 加一行即可；转储在 `%TEMP%\Age of Empires 3 DE\Data\data\`（**UTF-16**！先转码再 grep），是引擎合并后的实际数据（含 protoy/techtreey/civs/politiciandata/strings 及 **tactics/** 子目录，战术层可直接核验；按名核验用 scripts/verify-gamedata-dump.py）；**部署后自启 AoE3DE_s.exe（Steam 在跑）等 60~90s 即可重生成转储自验，无需真玩**，之后 taskkill 关闭。**本机实测（2026-09）**：`cmd //c start` 与直接起 exe 都静默失败（Steam 日志无记录），必须 `powershell -NoProfile -Command "Start-Process 'steam://rungameid/933110'"`（AoE3DE AppID=933110）才能拉起；关闭用 `powershell -NoProfile -Command "Stop-Process -Name AoE3DE_s -Force"`（taskkill 的 `//IM` 会被 MSYS 改写而报错）。转储 `%TEMP%\Age of Empires 3 DE\Data\data\` 含 protoy/techtreey/civs/politiciandata/strings/simplifiedchinese——把 mod 新增实体名/civmods 条目在转储里 count 一遍即端到端证据（civs 中重复 civ 名会被引擎合并，31≠32 属正常）。② 可直接 grep AoE3DE_s.exe：内含完整 `<flag>` 注册表（MagnetDoesNotLockUnits 邻域 ±3.5KB）与 HerdManager/BHerd/BHerdUnit 调试串；未用 flag 备选：CountHerdableAsGatherer/HerdablesIgnoreGatherPoint/GatherableByAllies。③ 战术文件以 .tactics.XMB 编译发布，但明文整文件覆盖经转储实测有效；官方附加式=`<type>.mods.tactics`+`<tacticsmods>`。④ 原版 train 按钮惯例：row 恒 0、column 可至 40+（自动排版）。⑤ 实战结论：同机官方萨米对照（诺伊迪+驯鹿）成立而自建单位零反应 → 存在靶侧准入条件（猜测集中在 Economic 系标记 / Military 系标记 / unitaitype，变体包验证中）。

## 军事旗帜/共享驻军传送网络（SharedGarrison+ejectAll）速查（2026-10 实战）

- **跨建筑"传送"机制**（原版 Commandery「可在任意其他 Commandery 部署驻军」的实现）：`<flag>SharedGarrison</flag>`（官方文档语义：驻守单位在所有带此标志的 protoUnit 实例间共享）+ `<flag>DeploymentUngarrison</flag>`（只能经部署命令弹出）+ `<deploymentcommand>命令</deploymentcommand>` + 命令定义 `<command>ejectAll(%d)</command>`+`<commandpassesunitid>`+`<deploy>`。→ 在 A 驻守、在 B 点「部署」= A→B 传送；驻军池按玩家全局共享（可让旗帜与指挥所共池）。范本：deCommandery（protoy id 2489）。容器还需 `<maxcontained>`+`<contain>`/`<notcontain>` 规则（indelay/outdelay 需 MeteredGarrison；克隆时整组拷全）。
- **按钮→点地图放置单位**：TempUnit power 仿 deAbilityInspiringFlag：`<createunit quantity="1" radius="0" delay="0.0" permanent="" singleinstance="">单位</createunit>`+`<placement forceonmap="1">full</placement>`+`<displayplacementruleserrors>1</displayplacementruleserrors>`+rangeindicatorprotoid(PowerRanger)+alwaysaddtoplayer。完整按钮三件：powermods 定义 power + protounitcommandmods 命令（associatedpower+castpower，缺 associatedtech 目前可用）+ 宿主 `<command page= column=>` 行 + abilitymods 条目（rof+donotforcestop；**DE 技能层即生成按钮**，同 dePowerMount）。singleinstance=同时至多一个实例（限量两面旗=两个不同 proto 各 1）。
- **视野字段**：protoy `<los>N.0000</los>`（deInspiringFlag=14、deCommandery=32）；`VisibleUnderFog` 雾中可见；`Invulnerable`/`Immoveable` 可做不可摧毁的固定节点。
- **核验注意**：转储 `abilities\abilities.xml` 会把块标签**统一转小写**（写 `<deCommandery2>` 转储成 `<decommandery2>`）——按 lower() 搜索；protoy/powers/protounitcommands/strings 转储均为合并结果可直接 grep。
- **GEMOD 实现（2026-10-10 交互迭代中）**：双旗变体包——壹号旗 GEMilitaryFlag（红图标，id 9954/900101）=变体A（+BuildingClass，对照陆地容器唯一先例 SPCFixedGunBase）；贰号旗 GEMilitaryFlagB（蓝图标，9953/900102）=变体B（Building+BuildingClass+全套指挥所驻军旗标）；两布设按钮（指挥所页2列1/列2）+ 收回 + 部署；替换=「延迟 1s 生成 + 辅助 RemoveUnits 清同型旧旗」；los 32；自绘图标；自建 placementrules。驻军准入与替换行为待实测（A/B 测试）。
- **经验沉淀（2026-10 实测驱动）**：①驻军准入：原版全库**无任何陆地非建筑容器**；唯一先例 SPCFixedGunBase（BuildingClass 无 Building）；Transport 标记（舰船家族）实测不解锁单位型目标驻军 ⇒ 疑需 BuildingClass/Building 类。②替换：`RemoveUnits` 是数据效果（target=Player，unittype=**原型名**；原版 deSloop 等在用）；powers 可携带 `<effect type="RemoveUnits">`（已合并，行为待实测）；`<createunit delay="1.0">` + aux = 顺序无关的“清旧+放新”。③SwapUnit 的 `abstracttype` 匹配对象疑为引擎类型表（exe 内大表）——**自定义标签疑似不识别**（轮转实测未生效）。④`<placementfile>` 自建规则文件可行。⑤bar 内 UI 图为混淆格式不可提取；自制图标用 PIL 自绘入 wpfg overlay。⑥buildlimit 对技能创建无效。
- **引擎约束（试做状态机时的教训，勿重复踩）**：powers 的 `<effect type>` 词表不含 TechStatus（power 无法翻转科技状态→「用完换下一个按钮」的状态机不可做）；单次施放只能一个落点（无两连点放置原语）；commandpassesunitid 只能传自身 id（无法寻址其他单位实例）→「一个按钮=撤销旧旗+自动重放两面」在纯数据层不可实现；可行替代仅：单实例替换语义（singleinstance，原版旗舰文案 'only one flag can be planted'）或轮换 swap（依赖 auxiliarypower 触发顺序，未验证）。可用控制台命令：deleteUnit(%d) 自删、ejectAll(%d) 弹驻军池（uiDeleteAllSelectedUnits 仅 UI 不可用）。
- **自定义 protounitCommand 必挂 associatedtech（2026-10 修「按钮可见但点不动」的根因）**：官方文档原文「AssociatedTech 定义命令的可用性/成本/研究时间」——缺失=命令不可用（按钮渲染但点击无效）。**最省事=复用原版常驻影子科技**：`DECommanderyDeploy`/`DEDepotDetonate` 由 AA Standard/Native/Asian/African StartingTechs（AAStandardStartingTechs/AANativeStartingTechs/YPAAAsianStartingTechs/DEAAAfricanStandardStartingTechs）对所有文明开局激活——AoP 成熟模组同款做法（zpStationDeploy 直接挂 DECommanderyDeploy）。原版 14 个 castpower 命令与 AoP 自定义命令 100% 带 associatedtech；**实测均无 dbid（mod 先例全无，文档声称的需求实践中未强制）**。GEMOD 另在 30 个 Age0 块补 TechStatus active 兜底；技能层 `<ability>` 同步带 `<tech>`（仿 deMarchRevolution）。

## Art/特效资源提取（.bar）速查

- 位置：`游戏安装\Game\Art\*.bar`；**特效/光环在 ArtEffects.bar**（effects\ypack_auras\*、chiefpower\*、projectiles、skybox 等，多为编译件 .XMB/.precomp + 原始件 .gr2/.ddt/.particle）；单位/建筑美术分在 ArtUnits/ArtBuildings.bar。
- bar 格式（ESPN v6，2026-10 实测）：'ESPN'+ver6 头；尾部=文件表，记录=`[f1,offset,z,s1,s2,s3 六个 u32][名长 u32][UTF-16 名]`——**字段在名字之前（读 nlen 前 24 字节）**，顺序读反会静默解出相邻文件的数据。f1=1=原样存储（s1 字节）；f1=0=LZ4：数据头 'alz4'+usize+csize，块解压。ddt 纹理可能另有混淆，工具按存储字节返回。
- 脚本：scripts/aoe3de-bar-extract.py（list / extract；f1=0 自动 LZ4 解压；2026-10 起多针扫描，UI.bar 也可直接 list/extract，必要时 --needle 定制）。
- **modelattachment 光环效果清单**（单位/建筑动作通用，配 `<modelattachmentbone>bonethatdoesntexist</modelattachmentbone>`）：effects\ypack_auras\{econpower=经济（引用 aura_econ 图标模型+Chiefpower 图标/环粒子）, american_power, daimyopower, frightpower, malta_power, papal_guard_power, speed_power, torpgatherpower, wettin_power}。

## 自定义UI（DE = WPF/XAML）速查（2026-10 实测）

- **DE 的 UI 全面 WPF/XAML 化**：旧版 gadget 教程（圣典 11 章）仅剧情编辑器适用。三层 + mod 覆盖法（整文件替换，无附加式）：
  1. 界面层：`Game\UI\UI.bar`（96MB）= 207 个明文 .xaml（UTF-8 BOM，raw 存储；另 7 个 ttf、1 个 sdfprecache.cache）。常用：`uimainnew.xaml`=游戏内 HUD（435KB；资源栏/小地图/胜利面板等 740 个 x:Name）、`uipregamenew.xaml`=主菜单、`uioptions.xaml`、`uipoliticiandlg.xaml`=政治家/领事弹窗、`uihomecitypanel.xaml`、`uitechtree.xaml`、`uimods.xaml`、`pages\<页名>\*.xaml`=子页面。mod 覆盖 = `<mod>\Data\wpfg\<同名相对路径>`。
  2. 资源层：`Game\UI\UIResources1-4.bar`（~10GB）。mod 覆盖 = `<mod>\Data\wpfg\resources\...`（同 bar 内相对路径）；习惯路径 `resources\images\icons\{techs,politicians,command,abilities,flags,random_map}\*.png`、`resources\art\{units,buildings}\...`。
  3. 数据层：Data.bar 内旧式 `ui*.xml`（uiconsulatedlg.xml、uitraderoutedlg.xml…）主 HUD 不用、**剧情编辑器工具仍在用**（AoP 覆盖 data\uitraderoutedlg.xml=编辑器贸易路线工具实证）；mod 覆盖 = `<mod>\Data\<同名>.xml`。文案走 stringmods.xml。
- **先例（可拆解学习）**：AoP(42687)：uipregamenew.xaml（661→500 行，删轮播）+ uipoliticiandlg.xaml + resources\images\icons\{techs 371、politicians 71、command 58、abilities 31、flags}；订阅 252113 怪物文明（resources\art\units\...）；94481 皮肤（icons\politicians、flags、eso）；GEMOD 的 random_map\gefort 已在用同机制。
- **边界**：XAML=纯视图层（x:Class="aoe3wpfg.*"，逻辑在 exe）；可改布局/图片/显隐/样式/增删可视元素，不可加功能或注册新窗口；保留 x:Class 与 Binding 名。UI 进不了 DebugOutputGameData，验证 = 进游戏看画面（改前备份）。
- 解包：scripts/aoe3de-bar-extract.py（多针扫描；`list`/`extract`；UI.bar 直接可用，必要时 --needle 定制）。Resource Manager GUI 亦可。

## 性能/画面卡顿排查速查（2026-10 实战）

- 取证位置：游戏自带性能记录 CSV = 用户数据\Logs\PerformanceMetrics\<玩家名>-<日期时间>.csv（UTF-16LE；每行=10 秒窗口均值）。**台阶值 15.4 / 30.8 / ~19.5 ≈ 当时帧率上限的 1/4、1/2、1/3**——帧时间超预算或显存换页的指纹；长段锁死此类台阶 = 硬性掉档而非随机波动。
- 图形设置实际文件 = 用户数据\Common\GraphicalProfile.xml（UTF-16）。windowmode=1 = BorderlessFullScreen；**无边框全屏下出图恒为桌面分辨率（日志 [D3D11Manager] resizeBuffers=桌面分辨率），把 optiongrfxres 改小不会减负；降载只能靠 OptionGrfxResolutionScale（渲染比例，配 OptionFSR）或直接改桌面分辨率**。2026-09-12 更新后该文件与更新自带 DefaultProfile 默认值趋同（无边框全屏+60 上限+FSR），排查性能问题时先核对是否被重置。
- 实时读数（游戏运行中，PowerShell）：GPU 占用 `Get-Counter '\GPU Engine(pid_<PID>*)\Utilization Percentage'`；整卡专用显存 `'\GPU Adapter Memory(*)\Dedicated Usage'`（4GB 卡实测 >3.6GB 即濒临打满，必卡）；分进程 `'\GPU Process Memory(*)\Dedicated Usage'`（各进程口径有重叠，仅供量级参考）。
- 本机环境事实：RX 580 4GB + 4K@60 桌面 → AOE3DE 重场景/RX580 帧时间超 16.7ms 即掉 15-30 台阶；常驻大户（Edge/QQ/酷狗 + DWM 合成实测 ~1.8GB 显存）与游戏抢 4GB 显存池；user.cfg 的 developer/aiDebug/showAIEchoes 增加开销（游戏内 resizeBuffers+显存报告刷屏=dev 标记日志噪音，与卡顿无因果）；GEMOD 与 Enhanced AI 同时启用会让 AI 侧双份开销。缓解：玩前清后台/重启，游戏内渲染比例降 50-60%、水面/阴影/粒子降档；长期=换显卡。
- Age3Log.txt 每启动覆盖：排查旧对局只能靠 PerformanceMetrics CSV；`_rundata.bin`、`RandMaps\Age3DERM*.dmp.txt`、`Trigger\trigtemp.xs` 为正常产物。

## 陷阱

- 文本写回必须保持原文件字节特征：BOM（utf-8-sig 读写会无条件加 BOM，GEMOD 的 .tactics/.xml/Art 多数无 BOM，protomods.xml 与 techtreemods.xml 有 BOM）与换行（以各文件实测为准：protomods/techtreemods=BOM+LF、strings=无BOM+LF、自定义 .tactics=无BOM+CRLF；改前逐文件量，勿凭经验）；用 `head -c 3 | xxd` 对比 git HEAD 版本再决定是否剥 BOM。
- 单位级内置 modify 版本文件（*.tactics、Art\*.xml）是整文件覆盖式，改前务必确认该文件只被目标单位引用（`grep '<tactics>' Data\protomods.xml`）；共享文件（handCavalry.tactics、musketBayonet.tactics 等）必须复制成 `<单位名>.tactics` 再改。

- AI 无 GUI 能力：Resource Manager / 3dsmax / Photoshop 等点界面步骤给用户操作指引；文件级修改（读基线、改 XML、部署、比对）全部自己做。
- 动画引用校验（改 animfile 后必做）：脚本提取 animfile 中全部 `<file>` 路径，逐一比对 sourceData/Data/Art 提取是否存在（先拿 us_cavalry_rider/horse、colonial_guardian 为对照确认提取完整），找不到＝运行时动画失效。
- mod 文件夹内同名 xml 覆盖游戏原文件；同目录 xml 与 xmb 并存时 **xmb 优先**（旧版按最后修改时间，DE 改为 xmb 优先）。
- 字符串必须放对应语言子目录（Data\strings\SimplifiedChinese\…），语言文件夹：SimplifiedChinese/TraditionalChinese/English/Japanese/Korean/French/German/Malay 等。
- info.json（MOD 根目录，{"Title","Author","Description"}）可选，缺省时模组界面显示文件夹名。
- 圣典以旧版为主：主城约 30%、UI 界面、UHC 章节（14 章）不适用于决定版（DE UI=WPF/XAML，见「自定义UI」速查；旧式 gadget 仅剧情编辑器适用）；DE 专章为 18 章（来源为 AoE3DE-Comprehensive-Data-Guide 官方文档的翻译，含 DE 新增属性如 DBID 要求）。
- 只有 XMB 的文件需先转换：Resource Manager → XMB to XML（排版乱，转后用格式化工具）；反方向同理。
- 修改不生效排查顺序：xmb 覆盖 → 语言目录 → 根节点/mergeMode → 模组启用与优先级（age3-mod-status.json）。
- 联机注意：部分修改会被判定影响联机；MOD 文件夹方式可规避部分检查，bar 打包（BAREditor→DataPY.bar）是旧版路线。

## 参考

- 路由表：G:\AOE3_mod\docs\AOE3DE_MOD开发-SOP路由表.md（需求→标准流程）
- 总流程：G:\AOE3_mod\docs\AOE3DE_MOD标准流程.md
- 分章 SOP 笔记（G:\AOE3_mod\refs\aoebbs_sacred_book\sop_notes\）：
  - ch18_de_specifics.md（DE 专章：提取/MOD文件夹/附加式/DE属性/决策表/GEMOD现状）
  - ch01-03_basics.md（protoy/techtreey/stringtabley、新单位/建筑/科技、AOE3ED）
  - ch04-07_civ_sound_card_tactics.md（civs/语音/卡片/Tactics）
  - ch08-13_anim_ability_ui_map.md（Animfile/技能/Data3/UI/地图简版）
  - ch13_maps.md（地图专章详版）
  - ch12-14-16-19_misc.md（案例/UHC/杂项/Startup）
  - ch00-15-17-97_refs.md（xml语法/函数表/模型/排障）
- 圣典本地索引：G:\AOE3_mod\refs\aoebbs_sacred_book\index.md（244 页按章）
- 附加式 MOD 明细：references/additive-mods.md
- 单位数值/平衡调整（数值所在层、damagebonus 语义、按原版基准的削弱/加强流程、单位块切片编辑法、报告格式）：references/unit-stats-and-balance.md
- exe 逆向（机制盘点静态字符串扫描第一步 + 进程转储反汇编管线）：references/exe-reverse-engineering.md
- 转储自验脚本：scripts/verify-gamedata-dump.py（按名检索 DebugOutputGameData 转储，核验新实体/科技/字串/战术的合并结果）
- 圣典站点重抓方法（Cloudflare+SPA）：cdp-browser-automation 技能「Bulk Capture Behind Anti-Bot Gates」
