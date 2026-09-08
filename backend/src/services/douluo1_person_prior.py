"""Curated person-identity knowledge for the original 斗罗大陆 novel.

Only aliases that identify the same concrete person across the original novel
belong in the alias groups below.  Context-dependent offices (院长/教皇/
大供奉) and overloaded concepts (蓝银皇/海神/修罗神) are intentionally kept
out: flattening those terms into a global alias map would corrupt time slices
and merge unrelated entities.

The first item of every group is the preferred canonical display name.
``persona`` groups represent a disguise or controlled identity; they are safe
for identity graph aggregation, while consumers that model narrative knowledge
may still preserve the alias as a time-bounded persona.
"""

from __future__ import annotations


STRICT_ALIAS_GROUPS: list[list[str]] = [
    ["唐三", "小三"],
    ["戴沐白", "沐白", "戴老大"],
    ["马红俊", "红俊", "胖子"],
    ["奥斯卡", "小奥"],
    ["宁荣荣", "荣荣"],
    ["朱竹清", "竹清"],
    ["玉小刚", "大师"],
    ["柳二龙", "二龙"],
    ["独孤博", "毒斗罗", "老怪物", "老毒物"],
    ["唐昊", "昊天斗罗"],
    ["宁风致", "宁宗主"],
    ["尘心", "剑斗罗", "剑道尘心", "剑爷爷"],
    ["古榕", "骨斗罗"],
    ["月关", "菊斗罗", "菊花关"],
    ["鬼魅", "鬼斗罗"],
    ["大明", "天青牛蟒"],
    ["二明", "泰坦巨猿"],
    ["波赛西", "海神斗罗"],
]


# Same underlying person, but the alias carries a narratively important state.
PERSONA_ALIAS_GROUPS: list[list[str]] = [
    ["千仞雪", "雪清河"],
    ["唐晨", "杀戮之王"],
]


# These terms need organization/location/time context and must never become
# unconditional aliases merely because they are frequent in this novel.
SCOPED_ROLE_TITLES = frozenset({
    "院长", "副院长", "教皇", "大供奉", "宗主", "队长", "老师",
})


# One surface form can denote a person, species, martial spirit, divine office,
# or abstract power.  Keep them out of person alias priors.
OVERLOADED_NON_PERSON_TERMS = frozenset({
    "蓝银皇", "海神", "修罗神", "罗刹神", "天使神", "柔骨兔",
})


def get_alias_groups() -> list[list[str]]:
    """Return defensive copies of graph-safe identity groups."""
    return [list(group) for group in STRICT_ALIAS_GROUPS + PERSONA_ALIAS_GROUPS]
