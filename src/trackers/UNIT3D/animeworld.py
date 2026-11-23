# Upload Assistant © 2025 Audionut & wastaken7 — Licensed under UAPL v1.0
import re
from pathlib import Path
from typing import Any, cast

import pycountry

from src.console import logger
from src.languages import languages_manager
from src.meta import Meta
from src.trackers.common import Common
from src.trackers.UNIT3D import UNIT3D


class AnimeWorld(UNIT3D):
    """
    AnimeWorld (AW) is a Private Torrent Tracker
    """

    tracker = "ANIMEWORLD"
    display_name = "AnimeWorld"
    supported_categories = ("MOVIE", "TV")
    base_url = "https://animeworld.cx"
    id_url = f"{base_url}/api/torrents/"
    upload_url = f"{base_url}/api/torrents/upload"
    search_url = f"{base_url}/api/torrents/filter"
    requests_url = f"{base_url}/api/requests/filter"
    torrent_url = f"{base_url}/torrents/"
    tracker_urls = ("https://animeworld.cx",)

    banned_groups = (
        "1XBET",
        "2dead",
        "HELD",
        "kala",
        "POE",
        "SHOWE",
        "SHOWEHD",
        "ORCA88",
        "LuRCH",
        "N2D2",
        "GETB8",
        "TFARC",
        "Kristallprinz",
        "LAW/CTFOH",
        "LAW",
        "CTFOH",
        "Pendeti",
        "FUN",
        "STARS",
        "Hugo",
        "hanime.tv",
        "ZeroStream",
        "Rikugou",
        "FSX",
        "Ta@",
        "Zerosins",
        "FireAnime",
        "DB",
        "Cleo",
        "bonkai77",
        "AnimeRG",
        "w00t",
        "SD7",
        "Anime2Enjoy",
        "KI-AI",
    )

    INVALID_TAG_PATTERN = re.compile(r"^(nogrp|nogroup|unknown|unk)$", re.IGNORECASE)
    WHITESPACE_PATTERN = re.compile(r"\s{2,}")
    MARKER_PATTERN = re.compile(r"\b(UNTOUCHED|VU1080|VU720|VU)\b", re.IGNORECASE)

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config, tracker_name=self.tracker)
        self.config = config
        self.common = Common(config)

    async def get_resolution_id(
        self,
        meta: Meta,
        resolution: str = "",
        reverse: bool = False,
        mapping_only: bool = False,
    ) -> dict[str, str]:
        """map each resolution to the correct id on the tracker"""
        resolution_id = {
            "4320p": "1",
            "2160p": "2",
            "1440p": "12",
            "1080p": "3",
            "1080i": "4",
            "720p": "5",
            "576p": "6",
            "576i": "7",
            "480p": "8",
            "480i": "9",
        }
        if mapping_only:
            return resolution_id
        if reverse:
            return {v: k for k, v in resolution_id.items()}
        if resolution:
            return {"resolution_id": resolution_id.get(resolution, "10")}
        meta_resolution = str(meta.resolution)
        resolved_id = resolution_id.get(meta_resolution, "10")
        return {"resolution_id": resolved_id}

    def get_basename(self, meta: Meta) -> str:
        """Extract basename from first file in filelist or path"""
        path_value = meta.path or "" if meta.isdir else next(iter(meta.filelist), meta.path or "")
        path = path_value if isinstance(path_value, str) else ""
        return Path(path).name

    def _get_language_code(self, track_or_string: Any) -> str:
        """Extract and normalize language to ISO alpha-2 code"""
        if isinstance(track_or_string, dict):
            track_dict = cast(dict[str, Any], track_or_string)
            lang = track_dict.get("Language", "")
            if isinstance(lang, dict):
                lang = cast(dict[str, Any], lang).get("String", "")
        else:
            lang = track_or_string
        if not lang:
            return ""
        lang_str = str(lang).lower()

        # Strip country code if present (e.g., "en-US" → "en")
        if "-" in lang_str:
            lang_str = lang_str.split("-")[0]

        if len(lang_str) == 2:
            return lang_str
        try:
            lang_obj: object = (  # pyright: ignore[reportUnknownVariableType]
                pycountry.languages.get(name=lang_str.title())  # pyright: ignore[reportUnknownMemberType]
                or pycountry.languages.get(alpha_2=lang_str)  # pyright: ignore[reportUnknownMemberType]
                or pycountry.languages.get(alpha_3=lang_str)  # pyright: ignore[reportUnknownMemberType]
            )
            alpha_2: object = getattr(lang_obj, "alpha_2", None) if lang_obj else None
            return alpha_2.lower() if isinstance(alpha_2, str) else lang_str
        except AttributeError, KeyError, LookupError:
            return lang_str

    def _get_german_title(self, imdb_info: dict[str, Any]) -> str | None:
        """Extract German title from IMDb AKAs with priority"""
        country_match: str | None = None
        language_match: str | None = None

        akas_value = imdb_info.get("akas", [])
        akas = cast(list[dict[str, Any]], akas_value) if isinstance(akas_value, list) else []
        for aka in akas:
            if aka.get("country") == "Germany" and not aka.get("attributes"):
                title = aka.get("title")
                if isinstance(title, str):
                    country_match = title
                    break  # Country match takes priority
            elif aka.get("language") == "German" and not language_match and not aka.get("attributes"):
                title = aka.get("title")
                if isinstance(title, str):
                    language_match = title

        return country_match or language_match

    def _has_german_audio(self, meta: Meta) -> bool:
        """Check for German audio tracks, excluding commentary"""
        mediainfo = meta.mediainfo
        if not mediainfo:
            return False

        tracks = mediainfo.get("media", {}).get("track", [])
        return any(track.get("@type") == "Audio" and self._get_language_code(track) in {"de"} and "commentary" not in str(track.get("Title", "")).lower() for track in tracks)

    def _has_german_subtitles(self, meta: Meta) -> bool:
        """Check for German subtitle tracks"""
        mediainfo = meta.mediainfo
        if not mediainfo:
            return False

        tracks = mediainfo.get("media", {}).get("track", [])
        return any(track.get("@type") == "Text" and self._get_language_code(track) in {"de"} for track in tracks)

    def _get_language_name(self, iso_code: str) -> str:
        """Convert ISO language code to full name (e.g. GERMAN, ENGLISH)"""
        if not iso_code:
            return ""

        iso_lower = iso_code.lower()

        # Try full language name (Italian, English, etc)
        lang: object = pycountry.languages.get(name=iso_code.title())  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if lang and hasattr(lang, "name"):
            name_val: object = getattr(lang, "name", "")
            return str(name_val).upper()

        # Try alpha_2 (IT, EN, etc)
        lang = pycountry.languages.get(alpha_2=iso_lower)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if lang and hasattr(lang, "name"):
            name_val = getattr(lang, "name", "")
            return str(name_val).upper()

        # Try alpha_3 (ITA, ENG, etc)
        lang = pycountry.languages.get(alpha_3=iso_lower)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if lang and hasattr(lang, "name"):
            name_val = getattr(lang, "name", "")
            return str(name_val).upper()

        return iso_code.upper()

    async def get_name(self, meta: Meta) -> dict[str, str]:
        """
        Rebuild release name from meta components following AnimeWorld naming rules.
        """
        if meta.manual_name is not None:
            return {"name": meta.manual_name.strip()}

        if not meta.language_checked:
            await languages_manager.process_desc_language(meta, tracker=self.tracker)

        # Title and basic info
        title = meta.title
        german_title = self._get_german_title(meta.imdb_info)
        use_german_title = self.config["TRACKERS"].get(self.tracker, {}).get("use_german_title", False)
        if german_title and use_german_title:
            title = german_title

        year_value: Any = meta.year or ""
        resolution_value: Any = meta.resolution
        source_value: Any = meta.source or ""
        year = str(year_value)
        resolution = str(resolution_value)
        source = (str(cast(Any, source_value[0])) if source_value else "") if isinstance(source_value, list) else str(source_value)
        video_codec = meta.video_codec
        video_encode = meta.video_encode

        # TV specific
        season = str(meta.season or "")
        episode = str(meta.episode or "")
        if "TV" in meta.category:
            year = ""

        # Optional fields
        edition = meta.edition
        hdr = meta.hdr
        uhd = str(meta.uhd or "")
        three_d = meta.three_d
        bit_depth = "10bit" if "10" in meta.bit_depth else ""

        # extract tags from basename for potential later use
        basename_up = self.get_basename(meta).upper()
        incomplete = "INCOMPLETE" if (meta.tv_pack and meta.season_pack_incomplete) or "INCOMPLETE" in basename_up else ""

        # Clean audio: remove Dual-Audio and trailing language codes
        audio = meta.audio
        if "DD+" in audio:
            audio = audio.replace("DD+", "DDP")

        # Build audio language tag
        audio_lang_str = ""
        if meta.audio_languages:
            # Normalize all to abbreviated ISO 639-3 codes
            audio_langs_value = meta.audio_languages
            audio_langs_raw = cast(list[Any], audio_langs_value) if isinstance(audio_langs_value, list) else []
            audio_langs = [self._get_language_name(str(lang)) for lang in audio_langs_raw]
            audio_langs = [lang for lang in audio_langs if lang]  # Remove empty
            audio_langs = list(dict.fromkeys(audio_langs))  # Dedupe preserving order

            num_langs = len(audio_langs)

            if num_langs == 1 and "GERMAN" in audio_langs:
                # One language (GERMAN)
                audio_lang_str = "German"

            elif num_langs == 2:
                # Two languages ("German.DL" if GERMAN is present, "[lang].DL" if not)
                if "GERMAN" in audio_langs:
                    audio_lang_str = "German.DL"
                elif "ENGLISH" in audio_langs:
                    audio_lang_str = "English.DL"
                else:
                    audio_lang_str = f"{audio_langs[0].title()} DL"

            elif num_langs >= 3:
                # Three or more languages, "German.ML" if GERMAN is present, "MULTI" only if not)
                audio_lang_str = "German.ML" if "GERMAN" in audio_langs else "MULTI"

        sub_langs_value = meta.subtitle_languages
        sub_langs_raw = cast(list[Any], sub_langs_value) if isinstance(sub_langs_value, list) else []
        sub_langs = [self._get_language_name(str(lang)) for lang in sub_langs_raw]
        sub_langs = [lang for lang in sub_langs if lang]  # Remove empty
        sub_langs = list(dict.fromkeys(sub_langs))  # Dedupe preserving order

        # Add [Ger.Sub] for German subtitles without German audio
        if not self._has_german_audio(meta) and self._has_german_subtitles(meta):
            audio_lang_str = "Ger.Eng.Sub" if "ENGLISH" in sub_langs else "Ger.Sub"


        effective_type = str(meta.type or "")

        source = source.replace("Blu-ray", "BluRay")

        # Detect Hybrid from filename if not in title
        hybrid = ""
        if not edition and (meta.webdv or isinstance(meta.source, list)) and "HYBRID" not in title.upper():
            hybrid = "Hybrid"

        repack = meta.repack.strip()

        name = None
        # Build name per AnimeWorld type-specific format
        if effective_type == "DISC":
            region = meta.region
            dvd_size = meta.dvd_size
            name = f"{title} {year} {season}{episode} {incomplete} {three_d} {edition} {audio_lang_str} {audio} {resolution} Untouched {region} {uhd} {source} {dvd_size} {hdr} {bit_depth} {video_codec} {repack}"
        elif effective_type == "REMUX":
            name = f"{title} {year} {season}{episode} {incomplete} {three_d} {edition} {hybrid} {audio_lang_str} {audio} {resolution} {uhd} {source} {hdr} {bit_depth} {video_codec} Remux {repack}"
        elif effective_type in ("DVDRIP", "BRRIP"):
            type_str = "DVDRip" if effective_type == "DVDRIP" else "BRRip"
            name = f"{title} {year} {season}{episode} {incomplete} {three_d} {edition} {hybrid} {audio_lang_str} {audio} {resolution} {type_str} {hdr} {bit_depth} {video_encode} {repack}"
        elif effective_type in ("ENCODE", "HDTV"):
            name = f"{title} {year} {season}{episode} {incomplete} {three_d} {edition} {hybrid} {audio_lang_str} {audio} {resolution} {uhd} {source} {hdr} {bit_depth} {video_encode} {repack}"
        elif effective_type in ("WEBDL", "WEBRIP"):
            service = str(meta.service or "")
            type_str = "WEB" if effective_type == "WEBDL" else "WebRip"
            name = f"{title} {year} {season}{episode} {incomplete} {three_d} {edition} {hybrid} {audio_lang_str} {audio} {resolution} {uhd} {service} {type_str} {hdr} {bit_depth} {video_encode} {repack}"
        else:
            logger.info(f"{self.tracker}: [bold red]Name enrichment failed. Please manually update the name after Uploading.[/bold red]")

        # Ensure name is always a string
        if not name:
            name = meta.name or "UNKNOWN"

        # Remove any leftover "Dual-Audio" markers
        if "Dual-Audio" in name:
            name = name.replace("Dual-Audio", "").strip()

        # Cleanup whitespace
        name = self.WHITESPACE_PATTERN.sub(" ", name).strip()
        name = name.replace(" ", ".")

        # Extract tag and append if valid
        tag = self._extract_clean_release_group(meta)
        if tag:
            name = f"{name}-{tag}"

        return {"name": name}

    def _extract_clean_release_group(self, meta: Meta) -> str:
        """Extract release group - only accepts VU/UNTOUCHED markers from filename"""
        raw_tag = meta.tag or ""
        tag = raw_tag.strip().lstrip("-") if isinstance(raw_tag, str) else ""
        if tag and " " not in tag and not self.INVALID_TAG_PATTERN.search(tag):
            return tag

        basename = self.get_basename(meta)
        # Get extension from mediainfo and remove it
        ext = meta.mediainfo.get("media", {}).get("track", [{}])[0].get("FileExtension", "")
        name_no_ext = basename[: -len(ext) - 1] if ext and basename.endswith(f".{ext}") else basename
        parts = re.split(r"[-.]", name_no_ext)
        if not parts:
            return "NOGRP"

        potential_tag = parts[-1].strip()
        # Handle space-separated components
        if " " in potential_tag:
            potential_tag = potential_tag.split()[-1]

        if not potential_tag or len(potential_tag) > 30 or not potential_tag.replace("_", "").isalnum():
            return "NOGRP"

        # ONLY accept if it's a VU/UNTOUCHED marker
        if not self.MARKER_PATTERN.search(potential_tag):
            return "NOGRP"

        return potential_tag

    async def get_additional_checks(self, meta: Meta) -> bool:
        """make sure the upload complies with the AW rules"""
        passed = True
        # Uploading MIC, CAM, TS, or LD releases, is prohibited.
        prohib_markers = ["MIC", "CAM", "TS", "TELESYNC", "LD", "LINE"]
        basename = self.get_basename(meta)
        # Split on delimiters (dot, hyphen, underscore) or whitespace so tags like "LD" only match as separate tokens
        basename_up = [tok for tok in re.split(r"[\.\s_-]+", str(basename).upper()) if tok]
        if any(x in basename_up for x in prohib_markers):
            logger.info(f"{self.tracker}: [bold red]Uploading MIC, CAM, TS or LD releases, is prohibited[/bold red]")
            passed = False

        # Uploading upscaled releases is prohibited. Exception: The release is from a group on the upscale whitelist
        if "UPSCALE" in basename_up:
            logger.info(f"{self.tracker}: [bold red]Uploading upscaled releases is prohibited, unless the group is is whitelisted {self.base_url}/pages/4[/bold red]")
            passed = False

        # Anime check
        if not meta.anime:
            logger.info(f"{self.tracker}: [bold red]Non-anime uploads are prohibited.[/bold red]")
            passed = False
        return passed

