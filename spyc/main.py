"""SPYC (pronounced spicy).

Usage:
    spyc plot xbar <dir> [<location>]... [--test_id=<id>] [--capability_loc=<loc>] [--verbose|--debug] [--meanline] [--violin]
    spyc -h | --help
    spyc --version

Options:
    -h --help              Show this screen.
    --version              Show version.
    -v --verbose           Verbose
    -d --debug             Debug Output
"""  # noqa

# Imports

import os
import glob
import logging
from typing import Optional

from mainentry import entry
from rich.console import Console
from rich.markdown import Markdown
from rich_dataframe import prettify  # type: ignore
from docopt import docopt  # type: ignore
import pandas as pd  # type: ignore

import dash  # type: ignore
import dash_core_components as dcc  # type: ignore
import dash_html_components as html  # type: ignore
from dash.dependencies import Input, Output  # type: ignore

# these imports will not work if ran as a script
# use python -m main
from .__init__ import __version__  # type: ignore
from .helpers.partnumber import PartNumber
from .helpers.spcfigure import SPCFigure

# create logger
log = logging.getLogger(__name__)
console = Console()

# Argument handling and setup
arguments = docopt(__doc__, version=f"SPYC {__version__}")

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# Manage verbose and debug output levels
if arguments["--verbose"] or arguments["--debug"]:

    def vprint(string: str, md: bool = False):
        """Only print if Verbose or Deubug option is given.

        Uses rich console print method.

        Parameters
        ----------
        string : str
            String to display
        md : bool, optional
            Interpret as Markdown
            Default False.
        """
        if md:
            console.print(Markdown(string))
        else:
            console.print(string)

    def vprettify(df: pd.DataFrame, **kwargs):
        """Table printing for verbose/debug.

        Parameters
        ----------
        df : pd.DataFrame
            dataframe to print
        **kwargs : str
            kwargs for rich-datafrme.prettify()
        """
        prettify(df, **kwargs)

    # Set logging threshold at info or debug
    if arguments["--debug"]:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=10)
    else:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=20)

else:

    def vprint(string: str, md: bool = False):
        """If not verbose dummy vprint.

        Parameters
        ----------
        string : str
            String to display
        md : bool, optional
            Interpret as Markdown, Default False
        """
        # pylint: disable=unused-argument

    def vprettify(df: pd.DataFrame, **kwargs):
        """If not verbose dummy vprettify.

        Parameters
        ----------
        df : pd.DataFrame
            dataframe to print
        **kwargs : str
            kwargs for rich-datafrme.prettify()
        """
        # pylint: disable=unused-argument

    # Set logging threshold at info
    logging.basicConfig(format="%(levelname)s: %(message)s", level=30)


def make_parts(filepath: str) -> list[PartNumber]:
    """Create list of parts in the target directory.

    Args:
        filepath (str): Directory to look within

    Returns:
        list[PartNumber]: Partslist
    """
    # Look up xlsx file in the specified directory
    data_files = glob.glob(f"{filepath}/*.xlsx")

    log.info(f"{len(data_files)} files found in {filepath}")

    # create Part_Number Object for each file
    parts = []
    for file in data_files:

        try:
            parts.append(PartNumber(file))
        except ValueError as e:
            log.warning(e)

    return parts


def dash_app(part_dict: dict[PartNumber, dict[str, SPCFigure]], debug=False):
    """Create a dash app."""
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    # build dict for part slection drop down
    part_dd_options = []
    for part in list(part_dict.keys()):

        part_dd_options.append(
            {
                "label": part.header["Part Number"],
                "value": part.header["Part Number"],
            }
        )

    disp_elements = [
        html.H1(children="SPYC"),
        html.Div(
            [
                dcc.Dropdown(
                    id="part_dd",
                    options=part_dd_options,
                    placeholder="Select a Part Number",
                    clearable=False,
                )
            ]
        ),
        html.Div(id="part_dd-output-container"),
    ]

    @app.callback(
        Output("part_dd-output-container", "children"),
        [Input("part_dd", "value")],
    )
    def display_graphs(value):
        """Display graphs selected by part number dropdown."""
        elements = []
        for part, figs in part_dict.items():
            # check if correct part
            if part.header["Part Number"] == value:
                # Add all plots for the one selected pn
                elements.append(html.H2(children=f"{part}"))
                for title, fig in figs.items():
                    elements.append(dcc.Graph(id=title, figure=fig))

        return elements

    app.layout = html.Div(children=disp_elements)

    app.run_server(debug=debug)


def plot(arguments: dict[str, str]):
    """Plot graphs from imported data."""
    # ensure path is absolute
    if os.path.isabs(arguments["<dir>"]):
        log.debug("dir input is absolute")
        filepath = arguments["<dir>"]
    else:
        log.debug("dir input is not absolute")
        filepath = os.path.abspath(arguments["<dir>"])

    log.debug(f"Looking in dir: {filepath}")

    parts = make_parts(filepath)

    # Dictionary of part numbers and figures
    # {PartNumber: {title: fig}}
    part_dict = {}

    for part in parts:

        # Raw Data
        vprint(f"# {part.header['Part Number']}", md=True)
        vprint("**Notes:**", md=True)
        vprint(f"{part.header['Notes']}", md=True)
        vprint("## Test List", md=True)
        vprettify(
            part.tests, first_rows=False, delay_time=1, clear_console=False
        )
        vprint("## Raw Data", md=True)
        for loc, data in part.data.items():
            vprint(f"## {loc}", md=True)
            vprettify(
                data.unstack(level=-1)["Reading"].merge(
                    part.tests, on="Test_ID", how="left"
                ),
                first_rows=False,
                delay_time=1,
                clear_console=False,
            )

        # launch dash interface

        if arguments["xbar"]:
            log.info("xbar plot")

            # if location argument is empty the nreplace it with None
            if arguments["<location>"]:
                locations: Optional[str] = arguments["<location>"]
            else:
                locations = None

            # Check locations are all in the PartNumber object
            if (
                locations is not None
                and set(locations).issubset(set(part.data.keys()))
            ) or locations is None:

                # Check capability_loc input
                if locations is None or (
                    arguments["--capability_loc"] in locations
                    or arguments["--capability_loc"] is None
                ):

                    meanline: bool = arguments["--meanline"]
                    violin: bool = arguments["--violin"]

                    # Plots for all sites all tests,
                    # calculate capability for Portland
                    figs = part.xbar(
                        location=locations,
                        test_id=arguments["--test_id"],
                        capability_loc=arguments["--capability_loc"],
                        meanline=meanline,
                        violin=violin,
                    )

                    # Add figs to part_dict
                    part_dict[part] = figs

                else:
                    log.error(
                        "Invalid capability_loc passed for PN:"
                        f" {part.header['Part Number']}\ncapability_loc"
                        " passed as :"
                        f" {arguments['--capability_loc']}\nLocations in"
                        f" input: {locations}"
                    )
                    raise ValueError("Invalid capability_loc")

            else:
                log.error(
                    "Invalid Locations passed for PN:"
                    f" {part.header['Part Number']}\nLocations passed as"
                    f" argument: {locations}\nLocations in data files:"
                    f" {part.data.keys()}"
                )
                raise ValueError("Invalid locations")

    # Launch dash app
    dash_app(part_dict, debug=arguments["--debug"])


@entry
def main():
    """Read user input from cli and call plot functions as required."""
    # Run command passed
    if arguments["plot"]:

        log.debug("Plot command")

        plot(arguments)


# Catch esceptions to use them as breakpoints
try:
    main()
except Exception as e:
    log.error(e)
