# Gemini 画图插件

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
