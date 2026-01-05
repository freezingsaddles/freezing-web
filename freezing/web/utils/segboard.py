import os
from typing import List

import yaml
from freezing.model.msg import BaseMessage, BaseSchema
from marshmallow import fields

from freezing.web.config import config
from freezing.web.exc import ObjectNotFound


class SegmentBoardSegment(BaseMessage):
    segment = None
    segment_name = None
    name = None
    description = None
    sponsors: List[int] | None = None
    banned: List[int] | None = None  # banned for prior win
    url = None


class SegmentBoardSegmentchema(BaseSchema):
    _model_class = SegmentBoardSegment

    segment = fields.Int(required=True)
    segment_name = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str()
    sponsors = fields.List(fields.Int())
    banned = fields.List(fields.Int())
    url = fields.Str()


class SegmentBoard(BaseMessage):
    segments: List[SegmentBoardSegment] = []


class SegmentBoardSchema(BaseSchema):
    _model_class = SegmentBoard

    segments = fields.Nested(SegmentBoardSegmentchema, many=True, required=True)


def load_segment(id) -> SegmentBoardSegment | None:
    path = os.path.join(config.LEADERBOARDS_DIR, "segment.yml")
    if not os.path.exists(path):
        raise ObjectNotFound("Could not find yaml board definition {}".format(path))

    with open(path, "rt", encoding="utf-8") as fp:
        doc = yaml.safe_load(fp)

    schema = SegmentBoardSchema()
    board: SegmentBoard = schema.load(doc)

    matches = [segment for segment in board.segments if segment.segment == id]

    return matches[0] if matches else None
