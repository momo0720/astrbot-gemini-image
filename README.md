# astrbot-gemini-image

可直接通过 AstrBot 插件仓库链接安装的独立插件仓库。

## 安装方式

### 方式一：通过 GitHub 链接安装

在 AstrBot 插件安装界面中填入本仓库链接即可。

### 方式二：手动安装

1. 克隆或下载本仓库。
2. 将仓库中的所有文件直接放入 AstrBot 的单个插件目录中。
3. 在 AstrBot 插件配置页填写所需配置。
4. 重启 AstrBot 或重载插件。

## 使用

- 主命令：`/gemini画图`
- 详细说明：见仓库内 `README.md` 下方内容

## 说明

- `metadata.yaml`、`main.py`、`_conf_schema.json` 已放在仓库根目录，兼容 AstrBot 链接安装。
- 已将本地敏感 API 地址和 Key 替换为占位内容（如适用）。
- 不包含运行环境中的本地配置文件。

---

通过 Gemini 兼容 `generateContent` 接口出图。

## 安装

1. 将 `gemini_image` 目录复制到 AstrBot 的插件目录中。
2. 在 AstrBot 插件配置页填写 `api_base_url`、`api_key` 和模型配置。
3. 重启 AstrBot 或重载插件后即可使用。

## 命令

- `/gemini画图 <提示词>`：默认模型 `gemini-3.1-flash-image-preview`，默认发送 `512` 分辨率，默认比例为 `9:16`
- `/gemini画图 1k <提示词>`：使用 1K 分辨率
- `/gemini画图 2k <提示词>`：使用 2K 分辨率
- `/gemini画图 pro <提示词>`：使用 `gemini-3-pro-image-preview`
- `/gemini画图 1k pro <提示词>`：使用 `gemini-3-pro-image-preview` 生成 1K 图片
- `/gemini画图 pro 1k <提示词>`：同上，参数顺序可互换
- `/gemini画图 2k pro <提示词>`：使用 `gemini-3-pro-image-preview` 生成 2K 图片
- `/gemini画图 <提示词> + 图片`
- `/gemini画图 <提示词> + @群友`：自动读取被 @ 群友的 QQ 头像并走图生图，支持一次附带多个 @ 头像
- `引用一张图片 + /gemini画图 <提示词>`
- `/gemini画图帮助`

## 当前适配接口

- API Base URL: `https://example.com/v1beta`
- 鉴权方式: `?key=<api-key>`
- 文生图 / 图生图接口: `POST /models/{model}:generateContent`
- 默认模型: `gemini-3.1-flash-image-preview`

## 行为

- 默认发送 `512` 分辨率，默认比例为 `9:16`
- `1k / 2k` 会通过 `generationConfig.imageConfig.imageSize` 传给 Gemini 接口
- `pro` 会切换到 `gemini-3-pro-image-preview`
- `pro` 和 `1k/2k` 顺序可互换
- 不带图时自动文生图
- 带图、引用图片或 @ 群友时自动图生图
- 图生图最多会提取 4 张参考图，来源可混合为引用图、直接图片和多个 @ 头像
- 默认自动重试 3 次，适用于超时、524、非 JSON、未返回图片等失败情况

## 比例规则

- 插件仍会在返回消息中推断显示比例
- 如果本次指定了 `1k/2k`，会同时携带推断出的 `aspectRatio`
- 你可以继续在提示词里描述：
  - `横图 / 横版 / 横屏 / landscape / wide`
  - `方图 / 正方形 / square / 1:1 / 头像`
  - `竖图 / 竖版 / 竖屏 / portrait / vertical / 全身 / 手机壁纸`
