from geoalchemy2.shape import to_shape

from app.models.story import Story


def geography_to_lat_lng(location: object) -> tuple[float, float]:
    """Return (lat, lng) from a PostGIS geography POINT."""
    pt = to_shape(location)
    return float(pt.y), float(pt.x)


def story_to_light_dict(story: Story) -> dict:
    lat, lng = geography_to_lat_lng(story.location)
    return {
        "id": story.id,
        "title_en": story.title_en,
        "title_zh": story.title_zh,
        "lat": lat,
        "lng": lng,
        "country": story.country,
        "emoji": story.emoji,
        "tags": list(story.tags) if story.tags else [],
    }


def story_to_full_dict(story: Story) -> dict:
    base = story_to_light_dict(story)
    base.update(
        {
            "content_en": story.content_en,
            "content_zh": story.content_zh,
        }
    )
    return base
