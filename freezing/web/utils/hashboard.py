import os
from typing import List

import yaml
from freezing.model.msg import BaseMessage, BaseSchema
from marshmallow import fields

from freezing.web.config import config
from freezing.web.exc import ObjectNotFound


class HashtagBoardTag(BaseMessage):
    tag = None
    alt = None
    name = None
    description = None
    sponsors: List[int] | None = None
    banned: List[int] | None = None  # banned for prior win
    url = None
    rank_by = None
    default_view = None
    extra_tab = None
    extra_body = None
    friendless = None
    min_miles = None


class HashtagBoardTagSchema(BaseSchema):
    _model_class = HashtagBoardTag

    tag = fields.Str(required=True)
    alt = fields.Str()
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    sponsors = fields.List(fields.Int())
    banned = fields.List(fields.Int())
    url = fields.Str()
    rank_by = fields.Str()
    default_view = fields.Str()
    extra_tab = fields.Str()
    extra_body = fields.Str()
    friendless = fields.Bool()
    min_miles = fields.Int()


class HashtagBoard(BaseMessage):
    tags: List[HashtagBoardTag] = []


class HashtagBoardSchema(BaseSchema):
    _model_class = HashtagBoard

    tags = fields.Nested(HashtagBoardTagSchema, many=True, required=True)


def load_hashtag(hashtag) -> HashtagBoardTag | None:
    path = os.path.join(config.LEADERBOARDS_DIR, "hashtag.yml")
    if not os.path.exists(path):
        raise ObjectNotFound("Could not find yaml board definition {}".format(path))

    with open(path, "rt", encoding="utf-8") as fp:
        doc = yaml.safe_load(fp)

    schema = HashtagBoardSchema()
    board: HashtagBoard = schema.load(doc)

    matches = [
        tag
        for tag in board.tags
        if tag.tag.lower() == hashtag.lower()
        or tag.alt
        and tag.alt.lower() == hashtag.lower()
    ]

    return matches[0] if matches else None
