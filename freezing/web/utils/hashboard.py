import decimal
import os
from typing import List

import yaml

from marshmallow import fields

from freezing.model.msg import BaseSchema, BaseMessage

from freezing.web.config import config
from freezing.web.exc import ObjectNotFound


class HashtagBoardTag(BaseMessage):
    tag = None
    name = None
    description = None
    url = None
    rank_by_rides = False


class HashtagBoardTagSchema(BaseSchema):
    _model_class = HashtagBoardTag

    tag = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    url = fields.Str()
    rank_by_rides = fields.Bool()


class HashtagBoard(BaseMessage):
    tags: List[HashtagBoardTag] = None


class HashtagBoardSchema(BaseSchema):
    _model_class = HashtagBoard

    tags = fields.Nested(HashtagBoardTagSchema, many=True, required=True)


def load_hashtag(hashtag) -> HashtagBoardTag:

    path = os.path.join(config.LEADERBOARDS_DIR, 'hashtag.yml')
    if not os.path.exists(path):
        raise ObjectNotFound("Could not find yaml board definition {}".format(path))

    with open(path, 'rt', encoding='utf-8') as fp:
        doc = yaml.load(fp)

    schema = HashtagBoardSchema()
    board: HashtagBoard = schema.load(doc)

    matches = [tag for tag in board.tags if tag.tag == hashtag]

    return None if len(matches) == 0 else matches[0]

