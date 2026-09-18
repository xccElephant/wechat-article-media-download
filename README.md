# wechat-article-media-download

中文 | [English](README_EN.md)

下载微信公众号文章内嵌的**全部视频和图片**，无需微信客户端、无需登录、无需任何 token。

[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 原理

微信公众号文章（`mp.weixin.qq.com/s/...`）的网页源码末尾，内嵌了一段 JS 数据块，其中**已经包含每个视频各 4 种清晰度的带签名直链**（`mpvideo.qpic.cn`，含 `dis_k` / `auth_key` 签名参数）。本工具直接从源码中提取这些直链并下载：

- 图片：`data-src` 属性中的 `mmbiz.qpic.cn` 公开地址，永久有效
- 视频：内嵌 JS 数据块中的签名直链，**约 7 天内有效**，支持并行下载
- 每个视频自动选择最佳清晰度（优先 `f10002` 超清 H.264）

不调用任何微信接口——`videoplayer` 系列接口目前已全部要求会话鉴权，匿名调用拿不到播放地址，此路不通。

## 安装

脚本为**单文件、零第三方依赖**（纯 Python 标准库），只需 Python 3.7+。

### 1. 安装 Python（已有可跳过）

**macOS**
```bash
python3 --version        # 先检查
brew install python      # 没有则安装
```
或从 [python.org/downloads](https://www.python.org/downloads/) 下载安装包。

**Windows**
- 从 [python.org/downloads](https://www.python.org/downloads/) 下载安装
- ⚠️ 安装时勾选 **"Add python.exe to PATH"**
- PowerShell 中验证：`python --version`

**Linux (Debian/Ubuntu)**
```bash
sudo apt update && sudo apt install -y python3
```

### 2. 获取脚本

```bash
git clone https://github.com/xccElephant/wechat-article-media-download.git
cd wechat-article-media-download

# 没有 git 也可以只下载单个文件：
# curl -O https://raw.githubusercontent.com/xccElephant/wechat-article-media-download/main/scripts/download.py
```

完毕——无需 `pip install`。

## 使用

```bash
# 仅依赖 Python 3.7+ 标准库，无需安装任何第三方包
python3 scripts/download.py <文章链接> [输出目录]

# 示例
python3 scripts/download.py "https://mp.weixin.qq.com/s/ICb4P_FqTZVgaeMvZs_9dg" ./output
```

输出结构：

```
output/
├── videos/          # video_01.mp4 ... 按文章出现顺序编号
├── images/          # image_01.png ... 自动识别 png/jpeg/gif 格式
└── sources.json     # 全部原始链接（便于追溯/重新下载）
```

## 条件与限制

| 条件 | 说明 |
|------|------|
| 文章可公开访问 | 不需要登录，普通浏览器能打开即可 |
| 签名有效期 | 视频直链抓取页面后约 1 周内有效，过期后重新运行即可 |
| Referer 请求头 | 脚本已自动携带，无需手动处理 |

**不适用的情况：**

1. 文章被删除 / 付费 / 仅粉丝可见 → 页面拿不到数据块
2. 视频来自**视频号**（Channels）而非公众号上传 → 源码中无 mpvideo 直链，需抓包获取
3. 文章含音频（voice）→ 暂未支持，音频走 `res.wx.qq.com/voice/getvoice?mediaid=` 另一条路

## 已知陷阱（给二次开发者）

- 直链在源码中以 `\x26amp;` 形式转义，**必须先还原为 `&` 再做正则提取**，否则 URL 在第一个 `&` 处截断，下载出 0 字节文件
- 分组时基础路径必须剥离 `.f\d+` 后缀（如 `xxx.f10002.mp4`），否则每种清晰度会被误判为一个独立视频（9 个视频变 36 组）
- 视频播放器 iframe 在桌面浏览器中 `src` 为空，播放模板页需要微信 JSBridge —— 浏览器自动化方案行不通，别浪费时间

## 目录结构

```
├── scripts/download.py   # 独立可运行脚本（零依赖）
├── SKILL.md              # AI Agent 技能文件（WorkBuddy / Claude Code 格式）
└── README.md
```

## 免责声明

仅供个人学习与资料备份使用，请尊重原作者版权，勿用于商业用途或二次传播。

## License

[MIT](LICENSE)
