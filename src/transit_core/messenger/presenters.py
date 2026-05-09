from transit_core.core.models import Arrival
from transit_core.messenger.views import Section, Table  # noqa: F401


def present_arrivals_board(arrivals: list[Arrival]) -> Section:
    rows: list[list[str]] = []

    for a in arrivals:
        rows.append(
            [
                a.route_id,
                a.direction,
                a.headsign if a.headsign else "",
                str(a.arrival_time),
            ]
        )

    result_table = Table(["Route ID", "Direction", "Destination", "Arrival Time"], rows)

    return Section("Arrivals", "Arrivals for station", result_table)
