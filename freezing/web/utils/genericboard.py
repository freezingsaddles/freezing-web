import decimal
import os
import enum
from datetime import datetime
from typing import List, Dict, Any, Tuple

import yaml

from marshmallow import fields
from marshmallow_enum import EnumField

from freezing.model import meta
from freezing.model.msg import BaseSchema, BaseMessage

from freezing.web.config import config
from freezing.web.exc import ObjectNotFound


class GenericBoardField(BaseMessage):

    name = None
    label = None
    type = None  # Do we need this ...?
    format = None
    visible: bool = True

    def format_value(self, v, row):

        if isinstance(v, str):
            if self.format:
                return self.format.format(**dict(row))
            else:
                return v

        elif isinstance(v, (float, decimal.Decimal)):
            # '{number:.{digits}f}'.format(number=p, digits=n)
            # {:,}
            if self.format:
                return self.format.format(v)
            else:
                return '{0:,.2f}'.format(v)

        elif isinstance(v, int):
            # '{number:.{digits}f}'.format(number=p, digits=n)
            # {:,}
            if self.format:
                return self.format.format(v)
            else:
                return '{0:,}'.format(v)

        elif isinstance(v, datetime):
            if self.format:
                return v.strftime(self.format)
            else:
                return v.isoformat()

        else:
            return v


class GenericBoardFieldSchema(BaseSchema):
    _model_class = GenericBoardField

    name = fields.Str()
    label = fields.Str()
    type = fields.Str()
    format = fields.Str()
    visible = fields.Bool()


class GenericBoard(BaseMessage):
    title = None
    description = None
    url = None
    query = None
    fields: List[GenericBoardField] = None


class GenericBoardSchema(BaseSchema):
    _model_class = GenericBoard

    title = fields.Str()
    description = fields.Str()
    url = fields.Str()
    query = fields.Str(required=True, allow_none=False)
    fields = fields.Nested(GenericBoardFieldSchema, many=True, required=False)


def load_board_and_data(leaderboard) -> Tuple[GenericBoard, List[Dict[str, Any]]]:

    path = os.path.join(config.LEADERBOARDS_DIR, '{}.yml'.format(os.path.basename(leaderboard)))
    if not os.path.exists(path):
        raise ObjectNotFound("Could not find yaml board definition {}".format(path))

    with open(path) as fp:
        doc = yaml.load(fp)

    schema = GenericBoardSchema()
    board: GenericBoard = schema.load(doc).data

    with meta.transaction_context(read_only=True) as session:

        rs = session.execute(board.query)

        if not board.fields:
            board.fields = [GenericBoardField(name=k, label=k) for k in rs.keys()]

        try:
            rows = [{f.name: f.format_value(row[f.name], row) for f in board.fields} for row in rs.fetchall()]
        except KeyError as ke:
            raise RuntimeError("Field not found in result row: {}".format(ke))

        return board, rows
