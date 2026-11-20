import asyncio

from src.meta import Meta
from src.trackers.UNIT3D.animeworld import AnimeWorld
from src.trackersetup import tracker_class_map


def _tracker() -> AnimeWorld:
    return AnimeWorld({"TRACKERS": {"ANIMEWORLD": {"use_german_title": True}}})


def test_animeworld_is_registered_with_full_tracker_name():
    assert tracker_class_map["ANIMEWORLD"] is AnimeWorld  # noqa: S101
    assert AnimeWorld.display_name == "AnimeWorld"  # noqa: S101


def test_animeworld_uses_release_directory_for_markers_and_group():
    tracker = _tracker()
    meta = Meta(
        isdir=True,
        path="/releases/Movie.2024.1080p.VU1080",
        filelist=["/releases/Movie.2024.1080p.VU1080/video.mkv"],
        anime=True,
    )
    assert tracker.get_basename(meta) == "Movie.2024.1080p.VU1080"  # noqa: S101
    assert tracker._extract_clean_release_group(meta) == "VU1080"  # noqa: S101


def test_animeworld_get_name_handles_german_title_and_audio():
    tracker = _tracker()
    meta = Meta(
        title="Original Title",
        year=2024,
        resolution="1080p",
        source="WEB-DL",
        type="WEBDL",
        audio="DD+ 5.1",
        audio_languages=["German", "Japanese"],
        language_checked=True,
        imdb_info={"akas": [{"country": "Germany", "title": "Deutscher Titel"}]},
        mediainfo={"media": {"track": [{"@type": "Audio", "Language": "German"}]}},
        anime=True,
    )
    name = asyncio.run(tracker.get_name(meta))["name"]
    assert name.startswith("Deutscher.Titel.2024")  # noqa: S101
    assert "German.DL" in name  # noqa: S101


def test_animeworld_rejects_unattended_prohibited_release():
    tracker = _tracker()
    meta = Meta(
        isdir=True,
        path="/releases/Movie.2024.CAM-GRP",
        filelist=["/releases/Movie.2024.CAM-GRP/movie.mkv"],
        unattended=True,
        requested_release=True,
        anime=True,
    )
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_animeworld_rejects_non_anime_release():
    tracker = _tracker()
    meta = Meta(
        isdir=True,
        path="/releases/Movie.2024-GRP",
        filelist=["/releases/Movie.2024-GRP/movie.mkv"],
        anime=False,
    )
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101
