# AOE3DE 附加式数据 MOD（Additive Data Mods）

来源：帝国时代3修改圣典 18 章（本地：`G:\AOE3_mod\refs\aoebbs_sacred_book\md\tutorial-18-23.md`、`tutorial-18-12.md`、`tutorial-18-0.md`）。

官方于 DE 后期更新加入。旧模式=复制基础数据文件并覆盖（游戏补丁后失效；两个 mod 改同一文件互斥）；附加模式=修改文件与基础数据合并（更新后仍有效，可与其他 mod 并存）。

## 文件映射表（原文件 → MOD 文件 → 根节点）

| 原文件 | MOD 文件 | 根节点 |
|---|---|---|
| protoy.xml | protomods.xml | <protomods> |
| techtreey.xml | techtreemods.xml | <techtreemods> |
| civs.xml | civmods.xml | <civmods> |
| politiciandata.xml | politicianmods.xml | <politicianmods> |
| nuggets.xml | nuggetmods.xml | <nuggetmods> |
| protounitcommands.xml | protounitcommandmods.xml | <protounitcommandmods> |
| cultures.xml | culturemods.xml | <culturemods> |
| maptypes.xml | maptypemods.xml | <maptypemods> |
| mapspecifictechs.xml | mapspecifictechmods.xml | <mapspecifictechmods> |
| attacktime.xml | attacktimemods.xml | <attacktimemods> |
| abilities\abilities.xml | abilities\abilitymods.xml | <abilitymods> |
| abilities\powers.xml | abilities\powermods.xml | <powermods> |
| randomnames.xml | randomnamemods.xml | <randomnamemods> |
| strings\<language>\*.xml | strings\<language>\stringmods.xml | <stringmods> |
| economymode.xml | economymodemods.xml | <economymodemods> |
| personalities.xml | personalitiesmods.xml | <personalitiesmods> |
| homecity<civ>.xml | homecity<civ>.mods.xml | <homecitymods> |
| tactics\<type>.tactics | tactics\<type>.mods.tactics | <tacticsmods> |
| uitechtree\techtreedata_<civ>.xml | uitechtree\techtreedata_<civ>.mods.xml | <uitechtreemods> |

## mergeMode

- 有效值：modify（在原有基础上修改）/ add（增加）/ remove（删除）/ replace（替换）。
- 缺省规则：基础数据中存在匹配节点 → modify；否则 → add。
- 字符串修改（stringmods）例外：无 mergeMode，直接写 <String _locID='...'>。

示例（摘录自 18-23）：

```xml
<protomods>
	<!-- 删除 -->
	<Unit mergeMode='remove' name='PropsPottedPlants'/>
	<!-- 修改：给单位加 Flag -->
	<Unit name='PropsPoles'><Flag>NotPlayerPlaceable</Flag></Unit>
	<!-- 修改：新增一个 Train 同时移除一个 -->
	<Unit name='Manor'>
		<Train row='0' page='1' column='2'>Longbowman</Train>
		<Train mergeMode='remove'>xpColonialMilitia</Train>
	</Unit>
	<!-- 替换 -->
	<Unit mergeMode='replace' id="1797" name='deIconUSCowboy'>...</Unit>
	<!-- 新增 -->
	<Unit name='MyNewProtoUnit'><DBID>2400</DBID>...</Unit>
</protomods>
```

```xml
<techtreemods>
	<Tech name='Age0Russian'>
		<Effects>
			<Effect mergeMode='add' type='Data' amount='1.00' subtype='Enable' relativity='Absolute'>
				<Target type='ProtoUnit'>Pikeman</Target>
			</Effect>
		</Effects>
	</Tech>
</techtreemods>
```

```xml
<stringmods>
	<StringTable>
		<Language name='English'>
			<String _locID='20038'>ModContinue</String>
		</Language>
	</StringTable>
</stringmods>
```

（工程实例：G:\AOE3_mod\workSpace\GEMOD\Data\protomods.xml 用 <unit>/<protoaction> 小写标签 + <rate mergeMode='add'> 亦可生效。）

## 验证：DebugOutputGameData

1. 在 `C:\<用户>\Games\Age of Empires 3 DE\<ID>\Startup\user.cfg` 加配置变量 `DebugOutputGameData`（文件不存在则创建）。
2. 游戏加载数据时，每个附加文件与基础数据合并后写出到 `%TEMP%\Age of Empires 3 DE\Data`。
3. 对比：先不启用 mod 导出一次，再启用 mod 导出，比较差异确认修改生效。

## 部署与优先级（18-12）

- MOD 文件夹：`%USERPROFILE%\Games\Age of Empires 3 DE\<SteamID>\mods\local\<MOD名>`；目录结构与游戏一致（Data、Art、Sound…）。
- 同名 xml 覆盖游戏原文件；同目录 xml 与 xmb 并存时 **xmb 优先**（与旧版按最后修改时间不同）。
- info.json（MOD 根目录）：`{"Title":"...","Author":"...","Description":"..."}`；缺省用文件夹名。
- 游戏内「工具→模组」启用/禁用/排序；`mods\age3-mod-status.json` 记录各 mod 的 Priority/Enabled。
