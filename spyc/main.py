"""SPYC (pronounced spicy)

Usage:
    spyc run <dir> [--verbose|--debug]
    spyc -h | --help
    spyc --version

Options:
    -h --help              Show this screen.
    --version              Show version.
    -v --verbose           Verbose
    -d --debug             Debug Output
"""

# Imports

import os
import glob
import logging

from mainentry import entry
from rich.console import Console
from rich.markdown import Markdown
from rich_dataframe import prettify  # type: ignore
from docopt import docopt  # type: ignore
import pandas as pd  # type: ignore


# these imports will not work if ran as a script
# use python -m main
from .__init__ import __version__  # type: ignore
from .helpers.partnumber import PartNumber


@entry
def main():
    """Main entry point"""

    # Argument handling and setup

    arguments = docopt(__doc__, version=f"SPYC {__version__}")

    # console config for rich outputs

    console = Console()

    # Manage verbose and debug output levels
    if arguments["--verbose"] or arguments["--debug"]:

        def vprint(string: str, md: bool = False):
            """
            Only print if Verbose or Deubug option is given,
            use rich console print method

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

        def vprettify(df: pd.DataFrame, **kwargs: str):
            """Table printing for verbose/debug

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
            """Dummy vprint to use if not verbose

            Parameters
            ----------
            string : str
                String to display
            md : bool, optional
                Interpret as Markdown, Default False
            """
            # pylint: disable=unused-argument
            pass

        def vprettify(df: pd.DataFrame, **kwargs: str):
            """Dummy vprettify to use if not verbose

            Parameters
            ----------
            df : pd.DataFrame
                dataframe to print
            **kwargs : str
                kwargs for rich-datafrme.prettify()
            """
            # pylint: disable=unused-argument
            pass

        # Set logging threshold at info
        logging.basicConfig(format="%(levelname)s: %(message)s", level=30)

    # create logger
    log = logging.getLogger(__name__)

    # Run command passed
    if arguments["run"]:

        log.debug("Run command")

        # ensure path is absolute
        if os.path.isabs(arguments["<dir>"]):
            filepath = arguments["<dir>"]
        else:
            filepath = os.path.abspath(arguments["<dir>"])

        # Look up xlsx file in the specified directory
        data_files = glob.glob(f"{filepath}/*.xlsx")

        vprint(f"{len(data_files)} files found in {filepath}")

        # create Part_Number Object for each file
        parts = []
        for file in data_files:
            parts.append(PartNumber(file))

            # Display outputs if verbose or debug
            for part in parts:

                vprint(part)

                # Raw Data
                vprint(f"# {part.header['Part Number']}", md=True)
                vprint("**Notes:**", md=True)
                vprint(f"{part.header['Notes']}", md=True)
                vprint("## Test List", md=True)
                vprettify(
                    part.tests,
                    first_rows=False,
                    delay_time=1,
                    clear_console=False,
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

                # Plots for all sites all tests,
                # calculate capability for Portland
                part.xbar(
                    capability_loc="Portland", meanline=True, violin=True
                )

                # Plots for 1 site 1 test
                part.xbar(
                    location="Miami", test_id="1", meanline=True, violin=True
                )

                # Plots for both sites 1 test
                part.xbar(
                    location=["Miami", "Portland"], test_id="2", meanline=True
                )


main()
