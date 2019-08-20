#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from api.cas import casadm
from api.cas.casadm import StatsFilter
from test_utils.size import Unit, Size, parse_unit
from datetime import timedelta
from typing import List
import re


def parse_stats_unit(unit: str):
    if unit is None:
        return ""

    unit = re.search(r".*[^\]]", unit).group()

    if unit == "s":
        return "s"
    elif unit == "%":
        return "%"
    elif unit == "Requests":
        return "requests"
    else:
        return parse_unit(unit)


def get_filter(filter: List[casadm.StatsFilter]):
    """Prepare list of statistic sections which should be retrieved and parsed. """
    if filter is None or StatsFilter.all in filter:
        _filter = [
            f for f in StatsFilter if (f != StatsFilter.all and f != StatsFilter.conf)
        ]
    else:
        _filter = [
            f for f in filter if (f != StatsFilter.all and f != StatsFilter.conf)
        ]

    return _filter


def get_statistics(
    cache_id: int,
    core_id: int = None,
    per_io_class: bool = False,
    io_class_id: int = None,
    filter: List[casadm.StatsFilter] = None,
    percentage_val: bool = False,
):
    stats = {}

    _filter = get_filter(filter)

    # No need to retrieve all stats if user specified only 'conf' flag
    if filter != [StatsFilter.conf]:
        csv_stats = casadm.print_statistics(
            cache_id=cache_id,
            core_id=core_id,
            per_io_class=per_io_class,
            io_class_id=io_class_id,
            filter=_filter,
            output_format=casadm.OutputFormat.csv,
        ).stdout.splitlines()

    if filter is None or StatsFilter.conf in filter or StatsFilter.all in filter:
        # Conf statistics have different unit or may have no unit at all. For parsing
        # convenience they are gathered separately. As this is only configuration stats
        # there is no risk they are divergent.
        conf_stats = casadm.print_statistics(
            cache_id=cache_id,
            core_id=core_id,
            per_io_class=per_io_class,
            io_class_id=io_class_id,
            filter=[StatsFilter.conf],
            output_format=casadm.OutputFormat.csv,
        ).stdout.splitlines()
        stat_keys = conf_stats[0]
        stat_values = conf_stats[1]
        for (name, val) in zip(stat_keys.split(","), stat_values.split(",")):
            # Some of configuration stats have no unit
            try:
                stat_name, stat_unit = name.split(" [")
            except ValueError:
                stat_name = name
                stat_unit = None

            stat_name = stat_name.lower()

            # 'dirty for' and 'cache size' stats occurs twice
            if stat_name in stats:
                continue

            stat_unit = parse_stats_unit(stat_unit)

            if isinstance(stat_unit, Unit):
                stats[stat_name] = Size(float(val), stat_unit)
            elif stat_unit == "s":
                stats[stat_name] = timedelta(seconds=int(val))
            elif stat_unit == "":
                # Some of stats without unit can be a number like IDs,
                # some of them can be string like device path
                try:
                    stats[stat_name] = float(val)
                except ValueError:
                    stats[stat_name] = val

    # No need to parse all stats if user specified only 'conf' flag
    if filter == [StatsFilter.conf]:
        return stats

    stat_keys = csv_stats[0]
    stat_values = csv_stats[1]
    for (name, val) in zip(stat_keys.split(","), stat_values.split(",")):
        if percentage_val and " [%]" in name:
            stats[name.split(" [")[0]] = val
        elif not percentage_val and "[%]" not in name:
            stat_name, stat_unit = name.split(" [")

            stat_unit = parse_stats_unit(stat_unit)

            stat_name = stat_name.lower()

            if isinstance(stat_unit, Unit):
                stats[stat_name] = Size(float(val), stat_unit)
            elif stat_unit == "requests":
                stats[stat_name] = float(val)
            else:
                raise ValueError(f"Invalid unit {stat_unit}")

    return stats
