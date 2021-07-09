"""SPYC (pronounced spicy).
  
  Usage:
      spyc plot <dir> [--verbose|--debug]
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
from typing import Optional, List, Dict, Any, Union

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

plot_types: List[str] = ["xbar"]

# Manage verbose and debug output levels
if arguments["--verbose"]:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=20)

elif arguments["--debug"]:
    # set to debug level
    logging.basicConfig(format="%(levelname)s: %(message)s", level=10)
else:
    # Set logging threshold at info
    logging.basicConfig(format="%(levelname)s: %(message)s", level=30)


def make_parts(filepath: str) -> Dict[str, PartNumber]:
    """Create list of parts in the target directory.

    Parameters
    ----------
    filepath : str
        Directory to look within

    Returns
    -------
    Dict[str, PartNumber]
        Partslist, key is part number string

    Raises
    ------
    ValueError
        Description
    """

    if not os.path.isabs(filepath):

        filepath = os.path.abspath(filepath)
        log.debug(f"dir input is not absolute, new dir is: {filepath}")

    log.debug(f"Looking in dir: {filepath}")

    # Look up xlsx file in the specified directory
    data_files = glob.glob(f"{filepath}/*.xlsx")

    log.info(f"{len(data_files)} files found in {filepath}")

    # create Part_Number Object for each file
    parts = {}
    for file in data_files:
        log.debug(f"Reading from {file}")
        try:
            part = PartNumber(file)
            if part.header["Part Number"] in parts:
                raise ValueError(
                    "Duplicate PN in source directory,"
                    f" {part.header['Part Number']}"
                )
            parts[part.header["Part Number"]] = part
        except ValueError as e:
            log.warning(e)

    return parts


def dash_app(filepath: str, debug: bool = False):
    """Create a dash app.

    Parameters
    ----------
    filepath : str
        Description
    debug : bool, optional
        Description

    Raises
    ------
    FileNotFoundError
        Description
    """
    app = dash.Dash(
        __name__, external_stylesheets=external_stylesheets, title="SPYC"
    )
    app.config["suppress_callback_exceptions"] = True

    # Get PartNumber objects
    part_dict = make_parts(filepath)

    if not part_dict:
        raise FileNotFoundError(
            f"No Parts generated from dir = {arguments['<dir>']}"
        )

    # build dict for part selection drop down
    part_dd_options = []
    for pn in list(part_dict.keys()):

        part_dd_options.append({"label": pn, "value": pn})

    # elements to always dispaly. The rest are generate by the code
    disp_elements = [
        html.H1(children="SPYC"),
        html.Div(
            [
                dcc.Dropdown(
                    id="part_dd",
                    options=part_dd_options,
                    placeholder="Select a Part Number",
                    clearable=True,
                )
            ]
        ),
        html.Div(id="part_dd_container"),
        html.Div(id="loc_dd_container"),
        html.Div(id="fig_container"),
    ]

    @app.callback(
        Output("part_dd_container", "children"), [Input("part_dd", "value")]
    )
    def get_loc(value: str) -> dcc.Dropdown:
        """Display graphs selected by part number dropdown.

        Parameters
        ----------
        value : str
            part number

        Returns
        -------
        dcc.Dropdown
            Dropdown of locations
        """

        # get part to plot from drop down value
        if value is not None:
            part = part_dict[value]

            # build dict for part slection drop down
            loc_dd_options = [{"label": "All", "value": "All"}]
            for loc in list(part.data.keys()):
                loc_dd_options.append({"label": loc, "value": loc})

            return dcc.Dropdown(
                id="loc_dd",
                options=loc_dd_options,
                placeholder="Select location(s)",
                clearable=True,
                multi=True,
            )

    @app.callback(
        Output("loc_dd_container", "children"), [Input("loc_dd", "value")]
    )
    def get_plot_type(value: str) -> dcc.Dropdown:
        """Display plot types avaialable.

        Parameters
        ----------
        value : str
            Description

        Returns
        -------
        dcc.Dropdown
            Description
        """

        plot_dd_options = []
        for ptype in plot_types:
            plot_dd_options.append({"label": ptype, "value": ptype})

        return dcc.Dropdown(
            id="plot_dd",
            options=plot_dd_options,
            placeholder="Select desired plot type:",
        )

    @app.callback(
        Output("fig_container", "children"),
        [
            Input("part_dd", "value"),
            Input("loc_dd", "value"),
            Input("plot_dd", "value"),
        ],
    )
    def plot_figure(pn: str, locs: List[str], ptype: str):
        """plot the figures.

        Parameters
        ----------
        pn : str
            Part Number to plot
        locs : str
            Lcoations to plot
        ptype : str
            Type of plot
        """
        # Get all inputs first
        if locs is not None and pn is not None and ptype is not None:

            part = part_dict[pn]
            # get part
            # SPCFigure uses none to indicate all locations
            if "All" in locs:
                locs = None

            elements = []

            for title, fig in plot_factory(part, ptype, locs).items():
                elements.append(html.H2(children=title))
                elements.append(html.Div(children=dcc.Graph(figure=fig)))

            return elements

    app.layout = html.Div(children=disp_elements)

    app.run_server(debug=debug)


def plot_factory(
    part: PartNumber, plot_type: str, locations: Union[List[str], None]
) -> Dict[str, SPCFigure]:
    """Create plot using parameters from the dash interface.

    Parameters
    ----------
    part : PartNumber
        PartNubmer object to plot for object
    plot_type : str
        Type of plot
    locations : Union[List[str], None]
        List of locations to plot for
    """
    # Select plot type
    if plot_type == "xbar":
        log.info("xbar plot")

        # Plots for all sites all tests,
        # calculate capability for Portland
        return part.xbar(
            location=locations,
            test_id=None,
            capability_loc=None,
            meanline=True,
            violin=True,
        )

        # TODO capability loc and test_id

        #     else:
        #         log.error(
        #             "Invalid capability_loc passed for PN:"
        #             f" {part.header['Part Number']}\ncapability_loc"
        #             " passed as :"
        #             f" {arguments['--capability_loc']}\nLocations in"
        #             f" input: {locations}"
        #         )
        #         raise ValueError("Invalid capability_loc")

        # else:
        #     log.error(
        #         "Invalid Locations passed for PN:"
        #         f" {part.header['Part Number']}\nLocations passed as"
        #         f" argument: {locations}\nLocations in data files:"
        #         f" {part.data.keys()}"
        #     )
        #     raise ValueError("Invalid locations")


@entry
def main():
    """Read user input from cli and call plot functions as required."""
    # Run command passed
    if arguments["plot"]:
        log.debug("Plot command")

        # Launch dash app
        dash_app(filepath=arguments["<dir>"], debug=arguments["--debug"])


# Catch exceptions to use them as breakpoints
try:
    main()
except Exception as e:
    log.error(e)
