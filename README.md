# astrbot-gemini-image

Generate images through Gemini-compatible generateContent endpoints.

## Features

- Supports text-to-image and image-to-image generation.
- Supports size options, model selection, quoted images, and avatar references.

## Installation

1. Clone or download this repository.
2. Copy the `gemini_image` directory into your AstrBot plugin directory.
3. Open the AstrBot plugin configuration page and fill in the required settings.
4. Restart AstrBot or reload the plugin.

## Usage

- Main command: `/gemini画图`
- Detailed command examples: see `gemini_image/README.md`

## Repository Structure

- `gemini_image/main.py`
- `gemini_image/_conf_schema.json`
- `gemini_image/metadata.yaml`
- `gemini_image/README.md`

## Notes

- Sensitive local API endpoints and keys have been replaced with placeholders where applicable.
- Runtime-specific local config files are not included.
