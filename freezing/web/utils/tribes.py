import os
from typing import List

import yaml
from freezing.model.msg import BaseMessage, BaseSchema
from marshmallow import fields

from freezing.web.config import config
from freezing.web.exc import ObjectNotFound


class TribalGroup(BaseMessage):
    name = None
    tribes: List[str] = None


class TribalGroupSchema(BaseSchema):
    _model_class = TribalGroup

    name = fields.Str(required=True)
    tribes = fields.List(fields.Str())


class TribalGroups(BaseMessage):
    tribal_groups: List[TribalGroup] = None


class TribalGroupsSchema(BaseSchema):
    _model_class = TribalGroups

    tribal_groups = fields.Nested(TribalGroupSchema, many=True, required=True)


def load_tribes() -> List[TribalGroup]:
    path = os.path.join(config.LEADERBOARDS_DIR, "tribes.yml")
    if not os.path.exists(path):
        raise ObjectNotFound("Could not find tribes definition {}".format(path))

    with open(path, "rt", encoding="utf-8") as fp:
        doc = yaml.safe_load(fp)

    schema = TribalGroupsSchema()
    groups = schema.load(doc)

    return groups.tribal_groups
