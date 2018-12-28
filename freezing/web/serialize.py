from marshmallow import Schema, fields

# shortcut
optional = dict(allow_none=True, required=False)


class AthleteSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    display_name = fields.String()
    team_id = fields.Integer(**optional)
    access_token = fields.String(**optional)
    refresh_token = fields.String(**optional)
    expires_at = fields.Integer()
    profile_photo = fields.String(**optional)

    # rides = orm.relationship("Ride", backref="athlete", lazy="dynamic", cascade="all, delete, delete-orphan")

class TeamSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    athletes = fields.Nested(AthleteSchema, many=True)


class RidePhotoSchema(Schema):
    id = fields.String()
    source = fields.Integer()
    ride_id = fields.Integer()
    ref = fields.String(**optional)
    caption = fields.String(**optional)

    img_t = fields.String(**optional)
    img_l = fields.String(**optional)

    primary = fields.Boolean()

    img_l_dimensions = fields.List(fields.Integer, dump_only=True)
