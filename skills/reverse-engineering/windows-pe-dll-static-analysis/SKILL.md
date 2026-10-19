---
name: windows-pe-dll-static-analysis
description: Use when analyzing a Windows PE or DLL in Ghidra.
version: 1.0.0
author: Masia
license: MIT
metadata:
  hermes:
    tags: [reverse-engineering, ghidra, pe, pdb, windows]
    related_skills: [reverse-skill]
---

# Windows PE / DLL 静态分析

实测流程：Windows + Ghidra 12.1.4 + JDK 25。

## When to Use

- 拿到不熟悉的 exe/dll，需要看导入导出、定位函数、反编译。
- 手上有 PDB，想把符号与签名回填到反汇编视图。

## 1. 侦察先行

- 用 pefile 读 machine、ImageBase、节表、导出、导入：判断架构、是否加壳、是否托管。
- 导出名与 Address Library ID 是后续定位函数的锚点；先把导出表存下来。
- 样本先算哈希再分析，能和发布页的校验值对上才继续。

## 2. 后端选择

- REA 的 Windows Ghidra provider 是 P0，只接受 executable 角色；DLL 会返回
  `target_role_unsupported`。不要在这条路上重试，直接 Ghidra headless。
- analyzeHeadless 要求项目目录已存在，否则抛 FileNotFoundException；先 mkdir。

## 3. headless 惯例

- 首次 `-import` 做全量分析；几百 KB 的 C++ DLL 约 3 分钟。
- 之后一律 `-process <name> -noanalysis` 复用工程，秒级。
- `-process` 不接受 `-save`（那是 `-import` 的参数）；脚本参数会吞掉它后面的 token。

## 4. Ghidra 脚本编译陷阱

Ghidra 把 deprecation 当错误，警告会表现成 ClassNotFoundException。

- `DemanglerUtil.demangle(Program,String)` 已废弃 → 用 `demangle(Program,String,Address)`。
- GhidraScript 没有 `setFunctionName(Function,String,SourceType)` → 用 `f.setName(name, SourceType)`。
- Function 没有 `getFullName()` → 用 `f.getSymbol().getName(true)`。

## 5. PDB 符号

- llvm-pdbutil 最稳：`dump -summary` 看是否剥离，`dump -publics` 取 S_PUB32。
- pdbparse PyPI 1.5 在现代 PDB 上崩（'NoneType' has no attribute 'name'）；用 moyix/pdbparse 的 git master。
- RVA = 段头 VirtualAddress + 符号 offset；先拿一个已知导出验证映射，再批量回填。
- 回填后用同一函数对比签名，确认 applyTo 是否套上了参数类型。

## 6. 行为地图

- 先按命名空间筛出目标自己的符号，再逐函数反编译串时序。
- 用字符串（日志、配置路径、构建机路径）交叉印证调用顺序。
- 依赖与兼容性判断通常在 GetModuleHandleW 里，能直接读出。
