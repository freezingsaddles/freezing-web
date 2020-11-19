from flask import render_template, Blueprint, session, redirect, request

from collections import defaultdict
from sqlalchemy import text

from freezing.model import meta
from freezing.model.orm import Tribe

from freezing.web.utils.auth import requires_auth
from freezing.web.utils.tribes import load_tribes

blueprint = Blueprint("tribes", __name__)


def query_tribes():
    athlete_id = session.get("athlete_id")
    if not athlete_id:
        return None

    tribes_q = meta.scoped_session().query(Tribe).filter(Tribe.athlete_id == athlete_id)

    my_tribes = defaultdict(str)
    for r in tribes_q:
        my_tribes[r.tribal_group] = r.tribe_name

    return my_tribes


@blueprint.route("/leaderboard")
def leaderboard():
    tribal_groups = load_tribes()
    my_tribes = query_tribes()

    tribe_stats = defaultdict(lambda: dict(distance=0, points=0, ride_days=0, riders=0))

    stats_query = text(
        """
        SELECT
            T.tribal_group,
            T.tribe_name,
            sum(B.distance) AS distance,
            sum(B.points) AS points,
            count(B.athlete_id) AS ride_days
        FROM tribes T JOIN daily_scores B ON T.athlete_id = B.athlete_id GROUP BY tribal_group, tribe_name;
        """
    )
    for t in meta.scoped_session().execute(stats_query).fetchall():
        tribe_stats[(t.tribal_group, t.tribe_name)].update(
            distance=round(t.distance), points=round(t.points), ride_days=t.ride_days
        )

    riders_query = text(
        """
        SELECT
            T.tribal_group,
            T.tribe_name,
            count(T.athlete_id) AS riders
        FROM tribes T GROUP BY tribal_group, tribe_name;
        """
    )
    for t in meta.scoped_session().execute(riders_query).fetchall():
        tribe_stats[(t.tribal_group, t.tribe_name)].update(riders=t.riders)

    maxima = defaultdict(dict)
    for tribal_group in tribal_groups:
        for metric in ["distance", "points", "ride_days"]:
            maxima[tribal_group.name][metric] = max(
                1,
                max(
                    tribe_stats[(tribal_group.name, tribe)][metric]
                    for tribe in tribal_group.tribes
                ),
            )

    return render_template(
        "tribes/leaderboard.html",
        tribal_groups=tribal_groups,
        my_tribes=my_tribes or defaultdict(str),
        maxima=maxima,
        stats=tribe_stats,
    )


@blueprint.route("/my")
@requires_auth
def my():
    tribal_groups = load_tribes()
    my_tribes = query_tribes()

    return render_template(
        "tribes/my.html", tribal_groups=tribal_groups, my_tribes=my_tribes
    )


@blueprint.route("/my", methods=["POST"])
@requires_auth
def post_my():
    athlete_id = session.get("athlete_id")
    tribal_groups = load_tribes()

    my_tribes = [
        dict(
            athlete_id=athlete_id,
            tribal_group=tribal_group.name,
            tribe_name=request.form.get(tribal_group.name),
        )
        for tribal_group in tribal_groups
        if request.form.get(tribal_group.name) in tribal_group.tribes
    ]

    meta.scoped_session().execute(
        Tribe.__table__.delete().where(Tribe.athlete_id == athlete_id)
    )

    meta.scoped_session().execute(Tribe.__table__.insert(), my_tribes)

    return redirect("/tribes/leaderboard")
