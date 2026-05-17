# README\.md

# 🇨🇳 CN IP List

自动维护最新中国大陆公网 IP 段，生成 RouterOS 可用地址列表。

## ✨ 项目说明

- 数据源：APNIC 官方IP库

- 自动更新：GitHub Actions 定时每日构建

- 输出格式：`\.rsc`（RouterOS 直接导入）

- 纯净无聚合、不合并网段、保留原始官方分段

## 📁 文件目录

```Plain Text
app/data/
├─ CN-IPv4.rsc       # 中国大陆 IPv4 段
├─ CN-IPv6.rsc       # 中国大陆 IPv6 段
├─ previous_*.json   # 历史备份数据
├─ diff_report.txt   # IP变动记录
└─ checksums.sha256  # 文件校验值
```

## 🔧 使用方法（RouterOS）

复制下面命令直接导入：

```Plain Text

/tool fetch url="https://raw.githubusercontent.com/HelloWorld-Shian/routerOS-CNIP/main/app/data/CN-IPv4.rsc" dst-path=CN-IPv4.rsc

/tool fetch url="https://raw.githubusercontent.com/HelloWorld-Shian/routerOS-CNIP/main/app/data/CN-IPv6.rsc" dst-path=CN-IPv6.rsc

/import file=CN-IPv4.rsc 
/import file=CN-IPv6.rsc 



```

## ⏰ 更新频率

默认 **每日自动更新**，自动对比网段变化、生成变更日志。

## 📌 特点

- 剔除内网、保留公网纯净网段

- 彩色简洁进度条，无冗余输出

- 本地/GitHub Actions 双兼容运行

- 自带 SHA256 文件校验

## 📃 License

Open Source，自由使用。

> （注：脚本内容由 AI 生成）
