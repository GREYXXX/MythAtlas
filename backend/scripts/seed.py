"""Load sample mythology stories. Run: python -m scripts.seed (from backend/)."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.story import Story
from app.services.embeddings import build_embedding_document, embed_text


SAMPLE_STORIES: list[dict] = [
    {
        "title_en": "The Monkey King Steals the Peaches of Immortality",
        "title_zh": "孙悟空大闹蟠桃园",
        "content_en": (
            "Sun Wukong, the stone-born trickster, leaps through clouds to the Peach Garden of Heaven. "
            "There he tastes fruits meant for the immortals, laughing at celestial law. His rebellion is "
            "not mere mischief—it is appetite for freedom, a spark that will shake the Jade Emperor’s court."
        ),
        "content_zh": (
            "石猴孙悟空腾云闯入天庭蟠桃园，偷食王母娘娘的仙桃。那不仅是顽皮，更是对天条的嘲弄与对自由的渴望，"
            "预示了后来大闹天宫的风暴。"
        ),
        "country": "China 中国",
        "tags": ["monkey", "immortality", "rebellion", "heaven", "ancient", "dragon"],
        "emoji": "🐒",
        "lat": 39.9042,
        "lng": 116.4074,
    },
    {
        "title_en": "Odysseus and the Cyclops",
        "title_zh": "奥德修斯与独眼巨人",
        "content_en": (
            "Trapped in Polyphemus’ cave, Odysseus names himself “Nobody.” When the giant is blinded and "
            "calls for help, his kin hear that Nobody has harmed him—and leave him to his fate. Cunning "
            "turns the monster’s strength against itself."
        ),
        "content_zh": (
            "奥德修斯被困独眼巨人波吕斐摩斯的洞穴，自称“无人”。巨人被刺瞎后呼救，族人听见“无人伤害我”便离去——"
            "智慧把蛮力引向自我毁灭。"
        ),
        "country": "Greece 希腊",
        "tags": ["odyssey", "cunning", "sea", "monster", "classical"],
        "emoji": "🧿",
        "lat": 37.9838,
        "lng": 23.7275,
    },
    {
        "title_en": "Ragnarök: Twilight of the Gods",
        "title_zh": "诸神的黄昏",
        "content_en": (
            "Wolf swallows the sun, serpent rises from the deep, and gods meet their destined ends on a "
            "field soaked with prophecy. From ash, the world is quietly made new—Norse myth’s stark hymn to "
            "cycles of ruin and renewal."
        ),
        "content_zh": (
            "巨狼吞日，巨蛇自海中升起，众神在预言铺就的战场上走向终局。北欧神话以冷峻的笔调书写毁灭与重生——"
            "世界在灰烬之后悄然更新。"
        ),
        "country": "Norse / Scandinavia 北欧",
        "tags": ["fate", "apocalypse", "gods", "renewal", "ancient", "flood", "sun"],
        "emoji": "⚔️",
        "lat": 59.9139,
        "lng": 10.7522,
    },
    {
        "title_en": "Amaterasu and the Cave of Heaven",
        "title_zh": "天照大神与天岩户",
        "content_en": (
            "Offended, the sun goddess Amaterasu retreats into a cave, plunging the world into darkness. "
            "The gods set a mirror and laughter outside until curiosity draws her forth—light returns, "
            "and order is restored through ceremony and joy."
        ),
        "content_zh": (
            "天照大神因不悦躲入天岩户，世界陷入黑暗。众神于洞外设镜与欢笑，以仪式与喜悦引她出洞——光复归，秩序重立。"
        ),
        "country": "Japan 日本",
        "tags": ["sun", "goddess", "light", "ritual", "ancient"],
        "emoji": "☀️",
        "lat": 34.4876,
        "lng": 136.7104,
    },
    {
        "title_en": "Anansi and the Sky God’s Stories",
        "title_zh": "阿南西与天神的故事",
        "content_en": (
            "The spider-trickster Anansi buys Nyame’s entire treasury of tales—not with gold, but with "
            "clever quests. Story becomes a bridge between worlds: small cunning earns the voice of a people."
        ),
        "content_zh": (
            "蜘蛛骗子阿南西用一连串机智任务，从天神尼亚姆手中换来全部故事。故事成为桥梁：微小的狡黠换来一个民族的声音。"
        ),
        "country": "West Africa 西非",
        "tags": ["trickster", "spider", "wisdom", "stories", "medieval"],
        "emoji": "🕷️",
        "lat": 5.6037,
        "lng": -0.1870,
    },
    {
        "title_en": "Raven Steals the Light",
        "title_zh": "乌鸦盗光",
        "content_en": (
            "In Pacific Northwest traditions, Raven opens a box and releases stars, moon, and sun—light "
            "spills across sea and forest. The theft is a gift: creation begins when someone dares to take "
            "what was hoarded."
        ),
        "content_zh": (
            "在太平洋西北岸的原住民叙事里，乌鸦打开匣子，放出星月与太阳，光洒向海与林。所谓“盗”，亦是馈赠："
            "创造始于敢于取回被囤积之物。"
        ),
        "country": "Indigenous North America 北美原住民",
        "tags": ["raven", "creation", "light", "coast", "ancient"],
        "emoji": "🪶",
        "lat": 54.5189,
        "lng": -130.3553,
    },
    {
        "title_en": "Rama, Sita, and the Bridge of Stones",
        "title_zh": "罗摩、悉多与石之桥",
        "content_en": (
            "To rescue Sita, monkeys and bears hurl mountains into the sea until a bridge rises—faith made "
            "geometry. The Ramayana turns devotion into engineering: love as a road others can walk."
        ),
        "content_zh": (
            "为救回悉多，猴军与熊族把山石投入大海，直到长桥浮现——信仰被写成几何。《罗摩衍那》把 devotion 变成工程："
            "爱是他人也能踏上的路。"
        ),
        "country": "India 印度",
        "tags": ["rama", "devotion", "bridge", "epic", "classical", "love", "princess"],
        "emoji": "🪷",
        "lat": 26.7920,
        "lng": 82.1998,
    },
    {
        "title_en": "Osiris Rises in the Duat",
        "title_zh": "奥西里斯于冥界复起",
        "content_en": (
            "Betrayed and scattered, Osiris is remembered whole by Isis and becomes lord of the dead. "
            "Egyptian myth ties kingship to return: what dies in pieces may still rule the horizon."
        ),
        "content_zh": (
            "奥西里斯被背叛、躯体散落，伊西丝使之复整，他成为冥界之主。埃及神话把王权与归来相连：碎裂之物仍可统治地平线。"
        ),
        "country": "Egypt 埃及",
        "tags": ["afterlife", "kingship", "resurrection", "nile", "ancient"],
        "emoji": "👁️",
        "lat": 26.1850,
        "lng": 31.9195,
    },
    {
        "title_en": "Cú Chulainn Takes Up Arms",
        "title_zh": "库丘林取枪",
        "content_en": (
            "A boy chooses weapons that only a king may lift—and destiny ignites. The Ulster Cycle’s hero "
            "is both protector and storm: glory and grief braided in a single spear-thrust."
        ),
        "content_zh": (
            "少年挑选只有王者才能举起的兵器，命运随之点燃。《阿尔斯特史诗》的英雄既是护盾也是风暴——荣耀与悲痛拧在一枪之上。"
        ),
        "country": "Ireland 爱尔兰",
        "tags": ["hero", "destiny", "war", "saga", "medieval"],
        "emoji": "🛡️",
        "lat": 54.3494,
        "lng": -6.6510,
    },
    {
        "title_en": "Quetzalcoatl at Teotihuacan",
        "title_zh": "羽蛇与特奥蒂瓦坎",
        "content_en": (
            "Feathered serpent winds through Mesoamerican imagination: creator, wind-bringer, boundary "
            "between earth and sky. At Teotihuacan’s avenues, myth walks in stone—time made architecture."
        ),
        "content_zh": (
            "羽蛇神盘绕在中美洲的想象之中：创造者、风的主宰、天地之间的界线。在特奥蒂瓦坎的大道上，神话以石头行走——时间被砌成建筑。"
        ),
        "country": "Mesoamerica 中美洲",
        "tags": ["feathered serpent", "creation", "pyramid", "wind", "classical", "fire"],
        "emoji": "🐍",
        "lat": 19.6925,
        "lng": -98.8437,
    },
    {
        "title_en": "Spirits of the Libyan Coast",
        "title_zh": "利比亚海岸的灵迹",
        "content_en": (
            "Along the Mediterranean rim, travelers swap tales of jinn-like spirits and luminous nights—"
            "stories that borrow from desert wind and salt. Here, myth is a harbor: every ship leaves a new ending."
        ),
        "content_zh": (
            "在地中海南岸，旅人交换关于灵怪与发光夜晚的故事——风与盐都渗入叙事。神话在此如港口：每艘船都带走一个新的结局。"
        ),
        "country": "Libya 利比亚",
        "tags": ["sea", "spirits", "desert", "journey", "moon", "modern"],
        "emoji": "🌙",
        "lat": 32.8872,
        "lng": 13.1913,
    },
    {
        "title_en": "The Rainbow Serpent Shapes the Land",
        "title_zh": "彩虹蛇塑造大地",
        "content_en": (
            "In Australian Aboriginal traditions, the Rainbow Serpent carves rivers and waterholes as it "
            "moves through Dreaming time—land is memory, and law is sung along its path."
        ),
        "content_zh": (
            "在澳大利亚原住民的梦世纪叙事中，彩虹蛇在时光中犁出水道与水潭——大地即记忆，律法在其路径上被唱出。"
        ),
        "country": "Australia 澳大利亚",
        "tags": ["dreaming", "serpent", "land", "law", "ancient"],
        "emoji": "🌈",
        "lat": -25.2744,
        "lng": 133.7751,
    },
]


async def _embed_all(session: AsyncSession) -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        return
    result = await session.execute(select(Story))
    stories = result.scalars().all()
    for s in stories:
        doc = build_embedding_document(s.title_en, s.title_zh, s.content_en, s.content_zh)
        try:
            s.embedding = await embed_text(doc)
        except Exception:
            continue
    await session.commit()


async def seed() -> None:
    async with async_session_factory() as session:
        n = await session.scalar(select(func.count()).select_from(Story))
        if n and int(n) > 0:
            print("Stories already present; skipping insert.")
            return

        for row in SAMPLE_STORIES:
            loc = WKTElement(f"POINT({row['lng']} {row['lat']})", srid=4326)
            session.add(
                Story(
                    title_en=row["title_en"],
                    title_zh=row["title_zh"],
                    content_en=row["content_en"],
                    content_zh=row["content_zh"],
                    country=row["country"],
                    tags=row["tags"],
                    emoji=row["emoji"],
                    location=loc,
                    embedding=None,
                )
            )
        await session.commit()
        print(f"Inserted {len(SAMPLE_STORIES)} stories.")

    async with async_session_factory() as session:
        await _embed_all(session)
        print("Embedding pass complete (skipped if no OPENAI_API_KEY).")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
