"""
Defines the layout of the Pixlet app for the Tidbyt device. This script needs to be rendered by an
environment with Pixlet installed.

In this implementation, it'll be a self-hosted version of the Axilla web Pixlet server.
https://github.com/btjones/axilla
"""

load("http.star", "http")
load("render.star", "render")
load("schema.star", "schema")


LINE_BACKGROUND_COLOR = '#16277e'


def main(config):
    bus1_line = config.str('bus1_line', '')
    bus1_headsign = config.str('bus1_headsign', '')
    bus1_next_times = config.str('bus1_next_times', '')

    bus2_line = config.str('bus2_line', '')
    bus2_headsign = config.str('bus2_headsign', '')
    bus2_next_times = config.str('bus2_next_times', '')

    return render.Root(
        child = render.Column(
            children = [
                bus_row(bus1_line, bus1_headsign, bus1_next_times),
                render.Box(
                    height = 1
                ),
                render.Box(
                    height=1,
                    color = '#fff'
                ),
                render.Box(
                    height=2
                ),
                bus_row(bus2_line, bus2_headsign, bus2_next_times)
            ],
        ),
    )


def bus_row(line, headsign, next_times):
    return render.Row(
                    children = [
                        render.Box(
                            color = LINE_BACKGROUND_COLOR,
                            width = 19,
                            height = 13,
                            child = render.Row(
                                children = [
                                    render.Box(
                                        width = 1,
                                    ),
                                    render.Text(content = line, font = "6x13"),
                                ],
                            ),
                        ),
                        render.Box(
                            width = 1,
                            height = 14,
                        ),
                        render.Column(
                            main_align = "start",
                            cross_align = "left",
                            children = [
                                render.Text(headsign, font = 'tom-thumb'),
                                render.Marquee(
                                    width = 46,
                                    child = render.Text(next_times, font = "tb-8", color = "#FFD580")
                                )
                            ],
                        ),
                    ],
                )


def get_schema():
    return schema.Schema(
        version = "1",
        fields = [
            schema.Text(
                id = "bus1_line",
                name = "Bus 1 Line Number",
                desc = "The line number of the first bus",
                icon = "bus",
            ),
            schema.Text(
                id = "bus1_headsign",
                name = "Bus 1 Headsign",
                desc = "The destination of the bus line",
                icon = "bus",
            ),
            schema.Text(
                id="bus1_next_times",
                name="Bus 1 Next Times",
                desc="A string describing the next arrivals, ex: '8:30AM  9:30AM",
                icon="bus",
            ),
            schema.Text(
                id="bus2_line",
                name="Bus 2 Line Number",
                desc="The line number of the first bus",
                icon="bus",
            ),
            schema.Text(
                id="bus2_headsign",
                name="Bus21 Headsign",
                desc="The destination of the bus line",
                icon="bus",
            ),
            schema.Text(
                id="bus2_next_times",
                name="Bus 2 Next Times",
                desc="A string describing the next arrivals, ex: '8:30AM  9:30AM",
                icon="bus",
            )
        ],
    )
