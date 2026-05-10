import asyncio
import base64
import re
from pathlib import Path

import aiohttp

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import At, Image, Reply
from astrbot.api.star import Context, Star


class GeminiImagePlugin(Star):
    """Gemini image plugin for Gemini-compatible generateContent endpoints."""

    DEFAULT_MODELS = [
        "gemini-3.1-flash-image-preview",
        "gemini-3-pro-image-preview",
    ]

    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        self.config = config or {}
        self._config_path = Path("data/config/gemini_image_config.json")

    def _cfg(self, key: str, default=None):
        return self.config.get(key, default)

    def _save_config(self) -> None:
        self._config_path.write_text(
            __import__("json").dumps(self.config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _get_models(self) -> list[str]:
        models = self._cfg("models", []) or []
        if isinstance(models, str):
            models = [line.strip() for line in models.splitlines() if line.strip()]
        normalized = [str(model).strip() for model in models if str(model).strip()]
        if normalized:
            return normalized

        legacy_model = str(self._cfg("model", "")).strip()
        if legacy_model:
            return [legacy_model]

        return list(self.DEFAULT_MODELS)

    def _get_default_model(self) -> str:
        models = self._get_models()
        return models[0] if models else ""

    def _get_blacklist(self) -> list[str]:
        blacklist = self._cfg("user_blacklist", []) or []
        if isinstance(blacklist, str):
            blacklist = [
                line.strip() for line in blacklist.splitlines() if line.strip()
            ]
        return [str(item).strip() for item in blacklist if str(item).strip()]

    def _set_blacklist(self, blacklist: list[str]) -> None:
        self.config["user_blacklist"] = blacklist
        self._save_config()

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        sender_id = str(event.get_sender_id())
        admins = self.context.get_config().get("admins_id", []) or []
        return sender_id in {str(item) for item in admins}

    def _extract_target_user_id(
        self, event: AstrMessageEvent, command: str
    ) -> str | None:
        for comp in event.message_obj.message:
            if isinstance(comp, At) and str(comp.qq) != "all":
                return str(comp.qq)

        target = event.message_str.strip()
        if target.startswith(f"/{command}"):
            target = target[len(f"/{command}") :].strip()
        elif target.startswith(command):
            target = target[len(command) :].strip()

        return target if target.isdigit() else None

    def _is_blocked_user(self, event: AstrMessageEvent) -> bool:
        sender_id = str(event.get_sender_id())
        return sender_id in set(self._get_blacklist())

    def _check_cfg(self) -> str | None:
        if not self._cfg("api_base_url"):
            return "❌ 插件未配置 API 地址。"
        if not self._cfg("api_key"):
            return "❌ 插件未配置 API Key。"
        if not self._get_models():
            return "❌ 插件未配置模型名称。"
        return None

    WIDE_KEYWORDS = [
        "横图",
        "横版",
        "横屏",
        "全景",
        "宽屏",
        "landscape",
        "wide",
        "panorama",
        "cinematic",
    ]
    SQUARE_KEYWORDS = [
        "方图",
        "正方形",
        "头像",
        "icon",
        "square",
        "1:1",
    ]
    TALL_KEYWORDS = [
        "竖图",
        "竖版",
        "竖屏",
        "全身",
        "手机壁纸",
        "portrait",
        "vertical",
        "9:16",
    ]

    def _get_default_aspect_ratio(self) -> str:
        return str(self._cfg("default_aspect_ratio", "9:16")).strip() or "9:16"

    def _infer_aspect_ratio(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if any(keyword in prompt_lower for keyword in self.WIDE_KEYWORDS):
            return "16:9"
        if any(keyword in prompt_lower for keyword in self.SQUARE_KEYWORDS):
            return "1:1"
        if any(keyword in prompt_lower for keyword in self.TALL_KEYWORDS):
            return "9:16"
        return self._get_default_aspect_ratio()

    def _resolve_model_size_and_prompt(
        self, prompt: str
    ) -> tuple[str, str | None, str]:
        prompt = prompt.strip()
        model = self._get_default_model()
        image_size: str | None = "512"
        models = self._get_models()
        remaining_parts: list[str] = []
        aspect_control_keywords = {
            *(keyword.lower() for keyword in self.WIDE_KEYWORDS),
            *(keyword.lower() for keyword in self.SQUARE_KEYWORDS),
            *(keyword.lower() for keyword in self.TALL_KEYWORDS),
        }

        for part in prompt.split():
            lowered = part.lower()
            if lowered in {"512", "1k", "2k"}:
                image_size = {
                    "512": "512",
                    "1k": "1K",
                    "2k": "2K",
                }[lowered]
                continue
            if lowered == "pro":
                model = "gemini-3-pro-image-preview"
                continue
            if lowered in aspect_control_keywords:
                continue
            if lowered.startswith("@") and lowered.endswith(")") and "(" in lowered:
                continue
            if part.isdigit():
                index = int(part) - 1
                if 0 <= index < len(models):
                    model = models[index]
                    continue
            remaining_parts.append(part)

        return model, image_size, " ".join(remaining_parts).strip()

    async def _read_image_component(self, comp: Image) -> bytes | None:
        try:
            image_path = await comp.convert_to_file_path()
            with open(image_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"读取输入图片失败: {e}")
            return None

    async def _get_avatar_bytes(self, user_id: str) -> bytes | None:
        if not str(user_id).isdigit():
            return None

        timeout = aiohttp.ClientTimeout(total=int(self._cfg("timeout", 180)))
        avatar_url = f"http://q4.qlogo.cn/g?b=qq&nk={user_id}&s=640"
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                avatar_bytes, error = await self._download_image(session, avatar_url)
            if error:
                logger.warning(f"读取头像失败，user_id={user_id}: {error}")
                return None
            return avatar_bytes
        except Exception as e:
            logger.warning(f"读取头像异常，user_id={user_id}: {e}")
            return None

    async def _get_images_from_event(
        self, event: AstrMessageEvent, max_count: int = 4
    ) -> list[bytes]:
        images = []

        async def _append_if_available(comp) -> bool:
            image_bytes = None
            if isinstance(comp, Image):
                image_bytes = await self._read_image_component(comp)
            elif isinstance(comp, At) and str(comp.qq) != "all":
                image_bytes = await self._get_avatar_bytes(str(comp.qq))

            if image_bytes:
                images.append(image_bytes)
                logger.info(
                    f"Gemini 画图收到参考图，来源={'@头像' if isinstance(comp, At) else '图片'}，当前数量={len(images)}/{max_count}"
                )
                return len(images) >= max_count
            return False

        for comp in event.message_obj.message:
            if isinstance(comp, Reply) and comp.chain:
                for quoted_comp in comp.chain:
                    if await _append_if_available(quoted_comp):
                        return images
            if await _append_if_available(comp):
                return images
        return images

    def _detect_mime_type(self, image_bytes: bytes) -> str:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if image_bytes.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        return "image/png"

    async def _download_image(
        self, session: aiohttp.ClientSession, url: str
    ) -> tuple[bytes | None, str | None]:
        retries = int(self._cfg("download_retries", 2))
        last_error = None
        for attempt in range(retries + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.read(), None
                    last_error = f"图片下载失败：HTTP {resp.status}"
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Gemini 图片下载异常，第 {attempt + 1}/{retries + 1} 次: {e}"
                )
            if attempt < retries:
                await asyncio.sleep(1)
        return None, last_error or "图片下载失败"

    def _decode_data_url(self, value: str) -> bytes | None:
        if not value.startswith("data:image/") or ";base64," not in value:
            return None
        try:
            return base64.b64decode(value.split(";base64,", 1)[1])
        except Exception as e:
            logger.warning(f"Gemini data URL 解码失败: {e}")
            return None

    async def _extract_image_bytes(
        self, session: aiohttp.ClientSession, data: dict
    ) -> tuple[bytes | None, str | None]:
        candidates = data.get("candidates") or []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                if not isinstance(part, dict):
                    continue

                inline_data = part.get("inlineData") or part.get("inline_data") or {}
                image_b64 = inline_data.get("data")
                if image_b64:
                    try:
                        return base64.b64decode(image_b64), None
                    except Exception as e:
                        return None, f"图片解码失败：{e}"

                file_data = part.get("fileData") or part.get("file_data") or {}
                file_uri = file_data.get("fileUri") or file_data.get("file_uri")
                if isinstance(file_uri, str) and file_uri.startswith(
                    ("http://", "https://")
                ):
                    return await self._download_image(session, file_uri)

                text_value = part.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    markdown_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", text_value)
                    if markdown_match:
                        image_ref = markdown_match.group(1)
                        data_url_bytes = self._decode_data_url(image_ref)
                        if data_url_bytes:
                            return data_url_bytes, None
                        if image_ref.startswith(("http://", "https://")):
                            return await self._download_image(session, image_ref)
                    data_url_bytes = self._decode_data_url(text_value.strip())
                    if data_url_bytes:
                        return data_url_bytes, None

        error = data.get("error", {}) if isinstance(data.get("error"), dict) else {}
        prompt_feedback = data.get("promptFeedback") or {}
        block_reason = prompt_feedback.get("blockReason")
        return (
            None,
            error.get("message")
            or block_reason
            or data.get("message")
            or "接口已响应，但未找到图片数据",
        )

    async def _generate_image(
        self,
        prompt: str,
        model: str,
        image_bytes_list: list[bytes] | None = None,
        image_size: str | None = None,
    ) -> tuple[bytes | None, str | None, str | None, str, str | None]:
        base_url = self._cfg("api_base_url").rstrip("/")
        api_key = self._cfg("api_key")
        timeout = aiohttp.ClientTimeout(total=int(self._cfg("timeout", 180)))
        retries = int(self._cfg("request_retries", 3))
        aspect_ratio = self._infer_aspect_ratio(prompt)
        image_bytes_list = image_bytes_list or []

        parts = [{"text": prompt}]
        for image_bytes in image_bytes_list:
            mime_type = self._detect_mime_type(image_bytes)
            parts.append(
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                }
            )

        generation_config = {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
            },
        }
        if image_size:
            generation_config["imageConfig"]["imageSize"] = image_size

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": generation_config,
        }

        last_error = None
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(retries + 1):
                try:
                    async with session.post(
                        f"{base_url}/models/{model}:generateContent?key={api_key}",
                        headers={"Content-Type": "application/json"},
                        json=payload,
                    ) as resp:
                        try:
                            data = await resp.json()
                        except Exception:
                            text = await resp.text()
                            last_error = (
                                f"接口返回非 JSON：HTTP {resp.status} {text[:300]}"
                            )
                            logger.warning(f"Gemini 画图非 JSON 响应: {last_error}")
                            if attempt < retries:
                                logger.info(
                                    f"Gemini 画图准备重试，原因=非JSON响应，model={model}，image_size={image_size}，第 {attempt + 2}/{retries + 1} 次"
                                )
                                await asyncio.sleep(1)
                                continue
                            break

                    if resp.status != 200:
                        error = (
                            data.get("error", {})
                            if isinstance(data.get("error"), dict)
                            else {}
                        )
                        last_error = (
                            error.get("message")
                            or data.get("message")
                            or f"HTTP {resp.status}"
                        )
                        logger.warning(
                            f"Gemini 画图失败，model={model}，image_size={image_size}，aspect_ratio={aspect_ratio}，image_count={len(image_bytes_list)}，尝试 {attempt + 1}/{retries + 1}，HTTP {resp.status}: {last_error}"
                        )
                        if attempt < retries:
                            logger.info(
                                f"Gemini 画图准备重试，原因=HTTP{resp.status}，model={model}，image_size={image_size}，第 {attempt + 2}/{retries + 1} 次"
                            )
                            await asyncio.sleep(1)
                            continue
                        break

                    image_result, error_message = await self._extract_image_bytes(
                        session, data
                    )
                    if image_result:
                        return image_result, None, model, aspect_ratio, image_size

                    last_error = error_message or "接口未返回图片"
                    if attempt < retries:
                        logger.info(
                            f"Gemini 画图准备重试，原因=未返回图片，model={model}，image_size={image_size}，第 {attempt + 2}/{retries + 1} 次"
                        )
                        await asyncio.sleep(1)
                        continue
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Gemini 请求异常，model={model}，image_size={image_size}，aspect_ratio={aspect_ratio}，image_count={len(image_bytes_list)}，尝试 {attempt + 1}/{retries + 1}: {e}"
                    )
                    if attempt < retries:
                        logger.info(
                            f"Gemini 画图准备重试，原因=请求异常，model={model}，image_size={image_size}，第 {attempt + 2}/{retries + 1} 次"
                        )
                        await asyncio.sleep(1)
                        continue
                    break
        return None, last_error or "画图请求失败", None, aspect_ratio, image_size

    @filter.command("gemini画图帮助")
    async def draw_help(self, event: AstrMessageEvent):
        model_lines = "\n".join(
            f"{index}. {model}"
            for index, model in enumerate(self._get_models(), start=1)
        )
        yield event.plain_result(
            "🎨 Gemini 画图插件\n"
            "命令：/gemini画图 <提示词>\n"
            "命令：/gemini画图 1k <提示词>\n"
            "命令：/gemini画图 2k <提示词>\n"
            "命令：/gemini画图 pro <提示词>\n"
            "命令：/gemini画图 1k pro <提示词>\n"
            "命令：/gemini画图 pro 2k <提示词>\n"
            "命令：/gemini画图 <提示词> + 图片\n"
            "命令：引用一张图片 + /gemini画图 <提示词>\n"
            f"默认模型：{self._get_default_model()}\n"
            "默认分辨率：512\n"
            f"默认比例：{self._get_default_aspect_ratio()}\n"
            "比例规则：默认 9:16，可按提示词自动匹配横图/方图/竖图\n"
            f"模型列表：\n{model_lines}"
        )

    @filter.command("gemini画图")
    async def draw_image(self, event: AstrMessageEvent):
        if self._is_blocked_user(event):
            yield event.plain_result("❌ 你已被加入该插件黑名单，无法使用此功能。")
            return

        err = self._check_cfg()
        if err:
            yield event.plain_result(err)
            return

        prompt = event.message_str.strip()
        if prompt.startswith("/gemini画图"):
            prompt = prompt[len("/gemini画图") :].strip()
        elif prompt.startswith("gemini画图"):
            prompt = prompt[len("gemini画图") :].strip()

        model, image_size, prompt = self._resolve_model_size_and_prompt(prompt)
        if not prompt:
            yield event.plain_result(
                "用法：/gemini画图 <提示词>、/gemini画图 1k <提示词>、/gemini画图 2k <提示词>、/gemini画图 pro <提示词>"
            )
            return

        image_inputs = await self._get_images_from_event(event, max_count=4)
        mode = "图生图" if image_inputs else "文生图"

        yield event.plain_result(f"🎨 正在进行[{mode}]，请稍候…")
        (
            image_bytes,
            error,
            used_model,
            aspect_ratio,
            used_image_size,
        ) = await self._generate_image(
            prompt, model, image_inputs, image_size=image_size
        )
        if error:
            yield event.plain_result(f"❌ 画图失败：{error}")
            return

        image_size_line = f"\n分辨率：{used_image_size}" if used_image_size else ""
        yield (
            event.make_result()
            .message(
                f"🖼️ 模式：{mode}\n模型：{used_model or model}{image_size_line}\n比例：{aspect_ratio}\n提示词：{prompt}"
            )
            .base64_image(base64.b64encode(image_bytes).decode())
        )
