# astrbot-gemini-image

一个通过 Gemini 兼容 generateContent 接口出图的 AstrBot 插件。

## 特性

- 支持文生图和图生图。
- 支持尺寸选项、模型切换、引用图片和头像参考图。

## 安装

1. 克隆或下载本仓库。
2. 将 `gemini_image` 目录复制到 AstrBot 的插件目录中。
3. 在 AstrBot 插件配置页填写所需配置。
4. 重启 AstrBot 或重载插件。

## 使用

- 主命令：`/gemini画图`
- 更多命令示例：见 `gemini_image/README.md`

## 仓库结构

- `gemini_image/main.py`
- `gemini_image/_conf_schema.json`
- `gemini_image/metadata.yaml`
- `gemini_image/README.md`

## 说明

- 已将本地敏感 API 地址和 Key 替换为占位内容（如适用）。
- 不包含运行环境中的本地配置文件。
