import decimal
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple

import yaml

from marshmallow import fields

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
    rank_by: bool = False

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
                return "{0:,.2f}".format(v)

        elif isinstance(v, int):
            # '{number:.{digits}f}'.format(number=p, digits=n)
            # {:,}
            if self.format:
                return self.format.format(v)
            else:
                return "{0:,}".format(v)

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
    rank_by = fields.Bool()


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
    board = load_board(leaderboard)

    with meta.transaction_context(read_only=True) as session:
        rs = session.execute(board.query)

        if not board.fields:
            board.fields = [GenericBoardField(name=k, label=k) for k in rs.keys()]

        rows = rs.fetchall()

        return board, format_rows(rows, board)


def load_board(leaderboard) -> GenericBoard:
    path = os.path.join(
        config.LEADERBOARDS_DIR, "{}.yml".format(os.path.basename(leaderboard))
    )
    if not os.path.exists(path):
        raise ObjectNotFound("Could not find yaml board definition {}".format(path))

    with open(path, "rt", encoding="utf-8") as fp:
        doc = yaml.load(fp, Loader=yaml.FullLoader)

    schema = GenericBoardSchema()
    board: GenericBoard = schema.load(doc)

    return board


def format_rows(rows, board) -> List[Dict[str, Any]]:
    try:
        formatted = [
            {f.name: f.format_value(row[f.name], row) for f in board.fields}
            for row in rows
        ]
        rank_by = next(iter([f.name for f in board.fields if f.rank_by]), None)
        return formatted if rank_by is None else rank_rows(formatted, rank_by)
    except KeyError as ke:
        raise RuntimeError("Field not found in result row: {}".format(ke))


def rank_rows(rows, rank_by, index=1, rank=0, rank_value=None) -> List[Dict[str, Any]]:
    if len(rows) == 0:
        return rows
    else:
        head, *tail = rows
        head_value = head[rank_by]
        head_rank = rank if index > 1 and head_value == rank_value else index
        return [{**head, "rank": head_rank}] + rank_rows(
            tail, rank_by, 1 + index, head_rank, head_value
        )
