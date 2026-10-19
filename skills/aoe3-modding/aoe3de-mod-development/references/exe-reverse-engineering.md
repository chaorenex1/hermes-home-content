# AoE3DE 可执行文件逆向管线（实测可行）

## 何时用
需要从引擎二进制确认机制行为（为何某 XML 机制不生效/生效条件）时；或盘点"引擎是否支持某机制/接受哪些 XML 节点"时（先跑下节轻量扫描）。

## 关键事实
- **磁盘上的 AoE3DE_s.exe 是加壳的**：.text/.text2 熵≈7.99（真实代码≈6-6.7），入口仅几条指令后即乱码。静态反汇编/字节扫描 .text 全废。数据段（.rdata/.pdata/.data）明文可读。
- **运行进程中的 .text 已完整解密**（熵≈6.4-6.75，100% 区段覆盖，主菜单状态即可）。
- 镜像 ASLR 重定位：本次 delta = 0x7FF586371200（每次启动会变，需按签名现算）。

## 轻量第一步：静态字符串扫描（盘机制先跑，无需启动游戏）

要答"引擎是否支持某机制/接受哪些 XML 节点"时先跑这个，秒级、零启动，往往一步就够（Teleport 盘点实证）：代码段加壳不可扫，但**字符串表/类型表/RTTI 名在磁盘 exe 明文可读**。

- 扫法：`data = open(exe,'rb').read(); low = data.lower()`；分别找 ASCII 与 UTF-16LE 两种编码的 needle（`'关键字'.encode('utf-16-le')`；`bytes.lower()` 对 UTF-16LE 的 ASCII 段同样有效，'T\x00e\x00…' 会被折成小写）。exe 里函数说明/报错串两种编码都有，类型枚举表与节点名多为 UTF-16LE；UTF-16 窗口起点先对齐偶数字节再解码。
- 命中窗口（±100~1400B）的产物与用途：
  - RTTI 类名族（如 `.?AVBProtoPowerTeleport@@`、`AVBPowerTeleport`）= 该机制有编译进去的类（给全族名）。
  - `parseNode` 报错串（如 `BProtoPowerTeleport::parseNode - invalid 'OutPortal' unit`）= 直接暴露 XML 合法节点名（报错串里出现的节点就是解析器认的字段）——比猜 schema 可靠。
  - 函数说明串（如 `trUnitTeleport : moves units from current position to…`）= 引擎脚本函数的官方语义。
  - 类型/枚举表（如 `TempUnit|SwapUnit|…|Teleport|…`）与字段名表（civs 类 `Ages|DisplayNameID|…`）= 数据可用的类型/字段全表。
- 随后用 sourceData 非 strings 全扫描（.xml/.xs/.tactics 读 bytes 找关键字）核对"引擎有、现数据是否用"：0 引用 = 引擎支持但未启用（可做实验包的候选机制）。
- 需要函数级行为（谁调用、什么条件）时再上下面的进程转储+反汇编重管线。

## 管线（工具在 G:\AOE3_mod\workSpace\tools\rev\）
1. 启动游戏（Steam），等 ~75s 到主菜单。
2. `dump_regions.py <procname> <outdir>`：VirtualQueryEx 枚举所有可执行内存区 + ReadProcessMemory 转储（358 区/175MB/3s）。
3. 定位镜像：在转储中找签名串如 `AbstractTypeHerdableMagnet`（命中 rdata 区）。
4. 求 delta：用多个已知字符串（原文件偏移 vs 转储偏移）联立；再重建连续 .text 镜像（text_mem.bin，旧 VA→文件偏移 = va-0x140001000）。
5. 用 capstone 在 text_mem.bin 上扫描（脚本 scan_mem.py / analyze_mem.py / disasm_fn_mem.py）。
6. 关闭游戏（dump 后即可 Stop-Process）。

## 已破解：protoUnitFlag 内部表示
- flag 注册表 = .rdata 指针数组（261 项），基址 0x14308FDA0（旧 VA）；索引即 flagID（与官方 tutorial-18-2 表一致）。
- **运行时存储 = 字节数组**：`test byte ptr [obj + flagID>>3], 1<<(flagID&7)`；置位用 `or/ bts`。
- 关键 ID：MagnetDoesNotLockUnits=193、AllowGatheringWhenFull=216、HerdablesIgnoreGatherPoint=212、CountHerdableAsGatherer=214、GatherersContributeToResourceRate=215、GatherableByAllies=200、UseAnimalsLabel=219。
- unittype 常量：AbstractTypeHuntableMagnet=1553(0x611)、HerdableMagnet=1554(0x612)。

## 已定位代码区（旧 VA）
- 0x140B0ED10-0x140B0FCF0：核心单位判定函数（同查 216+212+214+215+193 + 计数上限 + 资源累加）。
- 0x1411B5E70 / 0x1411B5FD0：检查 214/215/216 → `call 0x140B1B9E0(unit, N, 0)`（N 资源索引累加；0x15/0x13/0x17 等）。
- 0x140736310：查 193 + 条件 → `call 0x14072D7F0` 置位（or edx,4）。
- 0x1407EC8A0：另一处 193 消费者。
- BHerd/BUGA 野群 AI 簇 ≈0x140117C000-0x140118000（doGraze/doRestLogic/doMove、迁移 GoingToMigrate1/2）；GrazeAction ≈0x14011Axxx；调试串引用即函数锚点（herdmanager.cpp）。

## 陷阱
- capstone `skipdata` 伪指令（id==0）访问 operands 会抛 CsError，需跳过。
- RIP 相对引用换算：在旧 VA 空间反汇编时 `tgt_old = insn.address + insn.size + disp`（**不要**再减 delta）。
- 这些函数多为虚函数/回调：无直接 `call rel32` 调用者，需在 .rdata 扫 8 字节指针（vtable）找调用链。
- imm=193/216 大量为无关噪声（栈调整 0xc1/0xd8 等）；只用 `[reg+0x18/0x1b], mask` 字节测试形态定位真检查点。
