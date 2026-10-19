# 单位数值与攻击数值 · 平衡调整

适用：修改单位数值（移速/HP/成本/训练时间）、攻击数值（伤害/射程/ROF/伤害加成），以及按原版基准做"平衡调整"（削弱/加强）。改动落在工程 protomods.xml（附加式），完成后部署同步。

## 数值所在层（先定位，改错层=白改）

- 单位级字段 = `<unit>` 直接子节点：maxvelocity / maxrunvelocity（4 位小数格式，如 6.5000）、turnrate、初始/最大 HP、cost、trainpoints、allowedage、populationcount…
- 攻击数值 = 单位块内 `<protoaction>`：`<name>`、damage、damagetype、minrange/maxrange、rof（**单位=秒**，6 位小数格式）、damagecap、damagearea、projectile、damagebonus、damageflags。
- .tactics 文件通常**不含**战斗数值（只按名引用动作）——实测核对多门大炮的 tactics：damagebonus/rof/damage 计数全部为 0。改前仍对目标 tactics grep 一遍确认。
- **damagecap =「范围伤害上限」**（口径核实：字串 63681 cStringIncreaseDamageCap；wiki Area of Effect→Damage cap 节「limit the sum of damage by AoE attacks」）。语义：限制**一次 AoE 攻击造成的伤害总和**，计算先于乘数；原版惯例 = 2×基础伤害（践踏/齐射类 3×），全库主流符合（Falconet 100/200、GreatBombard 500/1000、Mortar 500/1000、各 2 号变体同）。科技可改：`<effect type="Data" action="攻击名" amount="1.50" subtype="DamageCap" relativity="BasePercent">`（原版唯一范本 ypMonasteryKillingBlowUpgrade）。调整口径惯性（四门重炮）：伤害 -25% 取整百 + damagecap ×1.5。
- tactics 里**没有** damagecap（全库普遍的 `<basedamagecap>1</basedamagecap>` 是另一回事，勿混）→ 只改 protomods 的 protoaction；共享基线 tactics 的单位（如 deSPC2 与 GreatBombard 共用 greatBombard.tactics）不受牵连。
- 语义外部核实（本机）：fandom 源站被 Cloudflare 拦、搜索站多被验证拦。wayback 直连可用：`curl -sL --compressed "https://web.archive.org/web/<ts>id_/<fandom页面>"`（不加 --compressed 会拿到压缩二进制；长文本落盘后按 80~100 字宽重整再读，否则被显示端省略）。
- damagebonus 语义：值 **>1 = 伤害加成**（对类型 ×N）；**<1 = 减伤/惩罚**。用户说"取消伤害加成"= **只删 >1.0 的项**；把 <1 的也删掉/置 1 反而是大幅加强（如对炮 0.4→1.0 变 2.5 倍伤害），会做反。

## 平衡调整工作流（锚定原版基准）

1. 对照：在工程 protomods 定位目标单位块；在 sourceData/Data/Data/protoy.xml 找**原版对应单位**（同族名/animfile 溯源），逐字段列出"被加强了多少"。
2. 定锚点：削弱移速优先回原版对应值（大炮族原版 3.5/5.5）。比例类调整（如发射间隔 ×1.5）用**统一规则**，在报告里给出每单位实际新值——用户按报告继续微调，通常一轮到位。
3. 编辑法（字节级）：按 `name="单位名"` 定位并**切片** `<unit ...>`…`</unit>`（`i = d.index(b' name="X">')` → `start = d.rindex(b'<unit ', 0, i)` → `end = d.index(b'</unit>', i) + len(b'</unit>')`），替换只在切片内做并断言 count==1；多单位改完整文件重建时按切片起点**倒序**拼接。**禁止整文件 replace 通用值**（6.5000 之类会误伤其它单位）。
4. damagebonus 清理：切片按行 split，正则 `<damagebonus type="([^"]+)">([0-9.]+)</damagebonus>` 逐行匹配，float(值)>1.0 才删行；断言每个单位预期删除数（锚点漂移即失败）。
5. 验证：ET.parse + BOM/换行字节校验 → git diff 评审 → 提交 → 部署 → diff -rq 全树=0。**纯数值调整无需重跑游戏转储**（转储只能证明数据合并、证明不了手感）；新增实体/结构（单位/科技/字串/动作）才值得跑一次转储端到端自验（scripts/verify-gamedata-dump.py）；手感由用户游戏内实测。
6. 报告格式：单位×字段 before→after 表；注明保留了哪些减伤项、哪些是可再调口径（成本/具体数值直接给新值让用户定）。

## 陷阱

- 字节比对两侧必须**同类构造**：行内容比行内容；一边带行尾换行另一边不带 = 假 mismatch，白排查一轮。
- protomods 中 `<unit id>` **可重复共存**且游戏正常加载（实测重复 id 无碍）；发现重复不要擅自改 id——先报告（可能有别处按数字引用）。
- rof 数值越大发射越慢："增加发射间隔" = rof 调大，不要反向。
