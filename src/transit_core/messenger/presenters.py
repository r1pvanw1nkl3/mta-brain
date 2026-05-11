import time

from transit_core.core.models import (
    ArrivalsBoard,
    NearbyArrivalsResult,
    NearbyStopsResult,
    StopSearchResult,
)
from transit_core.messenger.views import Section, Stack, Table, View


def _minutes_until(arrival_epoch: int, now: int) -> str:
    mins = max(0, round((arrival_epoch - now) / 60))
    return "now" if mins == 0 else f"{mins} min"


def present_help() -> Section:
    rows = [
        ["!arrivals <stop_id>", "Arrivals for a GTFS Stop ID"],
        ["!search <search query>", "Station search by name"],
        ["!nearby <address>", "Find stops near an address"],
        ["!planner <address", "See departure boards for stops near an address"],
    ]

    table = Table(["Command", "Description"], rows)

    return Section("Help", "Available commands", table)


def present_arrivals_board(
    arrivals_board: ArrivalsBoard, now: int | None = None
) -> Section:
    subtitle = f"Arrivals for {arrivals_board.stop_name}"

    if not arrivals_board.arrivals:
        return Section("Arrivals", subtitle, "No upcoming arrivals.")

    now = now if now is not None else int(time.time())

    rows = [
        [
            a.route_id,
            a.direction,
            a.headsign or "",
            _minutes_until(a.arrival_time, now),
        ]
        for a in arrivals_board.arrivals
    ]

    table = Table(["Route", "Direction", "Destination", "ETA"], rows)
    return Section("Arrivals", subtitle, table)


def present_stop_search_results(results: list[StopSearchResult], query: str) -> Section:
    subtitle = f'Stops matching "{query}"'

    if not results:
        return Section("Stop Search", subtitle, "No matching stops.")

    rows = [[r.stop_id, r.stop_name, r.routes] for r in results]
    table = Table(["Stop ID", "Name", "Routes"], rows)
    return Section("Stop Search", subtitle, table)


def present_nearby_stops(result: NearbyStopsResult | None, query: str) -> Section:
    subtitle = f'Stops near "{query}"'

    if result is None:
        return Section(
            "Nearby Stops",
            subtitle,
            "Couldn't find that address. Try adding a borough or neighborhood.",
        )

    matched_subtitle = f"{subtitle} — matched: {result.matched_address}"

    if not result.stops:
        return Section(
            "Nearby Stops", matched_subtitle, "No subway stops found nearby."
        )

    rows = [
        [s.gtfs_stop_id, s.stop_name, s.line, f"{int(s.dist_meters)} m"]
        for s in result.stops
    ]
    table = Table(["Stop ID", "Name", "Line", "Distance"], rows)
    return Section("Nearby Stops", matched_subtitle, table)


def present_nearby_arrivals(
    result: NearbyArrivalsResult | None,
    query: str,
    max_walk_time_mins: int,
    max_per_stop: int = 5,
    now: int | None = None,
) -> Section:
    subtitle = f'Arrivals near "{query}" (within {max_walk_time_mins} min walk)'

    if result is None:
        return Section(
            "Nearby Arrivals",
            subtitle,
            "Couldn't find that address. Try adding a borough or neighborhood.",
        )

    matched_subtitle = f"{subtitle} — matched: {result.matched_address}"

    if not result.arrivals:
        return Section(
            "Nearby Arrivals",
            matched_subtitle,
            f"No subway stops within {max_walk_time_mins} min walk.",
        )

    now = now if now is not None else int(time.time())

    sub_sections: list[View] = []
    for board in result.arrivals:
        if not board.arrivals or board.walk_time is None:
            continue

        walk_seconds = board.walk_time * 60
        makeable = [a for a in board.arrivals if a.arrival_time - now >= walk_seconds][
            :max_per_stop
        ]

        if not makeable:
            continue

        rows = [
            [
                a.route_id,
                a.direction,
                a.headsign or "",
                _minutes_until(a.arrival_time, now),
            ]
            for a in makeable
        ]
        sub_sections.append(
            Section(
                board.stop_name,
                f"{round(board.walk_time)} min walk",
                Table(["Route", "Dir", "Destination", "ETA"], rows),
            )
        )

    if not sub_sections:
        return Section(
            "Nearby Arrivals",
            matched_subtitle,
            "No upcoming arrivals at nearby stops.",
        )

    return Section("Nearby Arrivals", matched_subtitle, Stack(sub_sections))
