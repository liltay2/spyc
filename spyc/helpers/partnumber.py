"""Importing and manipualting
test data for individual part numbers,
some basic structure to call on the SPCFigure library
"""

# Imports

import statistics
import logging
from typing import Union, Tuple, Optional
import pandas as pd  # type: ignore
import numpy as np
from .spcfigure import SPCFigure  # type: ignore


class PartNumber:
    """
    Object to represent a single part number
    and its associated test data and methods

    See "Dummy Data.xlsx" for an example input data file

    Deleted Attributes
    ------------------
    log : logging:Logger
        logging object
    data : dict[str, pd.Dataframe]
        Dictionary of data frames
        containing raw test data
    header : dict[str,str]
        Dict of outline infomation
    tests : pd.Dataframe
        Dataframe with test descriptions
    """

    def __init__(self, filepath: str) -> None:
        """Set up logging and read in data from filepath

        Parameters
        ----------
        filepath : str
            path to data file
        """
        # self.log object
        self.log: logging.Logger = logging.getLogger(__name__)

        # Read from excel
        try:

            col_dtype = {
                "Part Number": "string",
                "Notes": "string",
                "Test_ID": "string",
                "Test_Name": "string",
                "Min_Tol": np.float64,
                "Max_Tol": np.float64,
                "Units": "string",
                "Reading": np.float64,
            }

            # Single call to Excel
            xls = pd.ExcelFile(filepath)

            # Generic header infomation
            self.header: dict[str, str] = (
                pd.read_excel(xls, sheet_name="Header", dtype=col_dtype)
                .iloc[0]
                .to_dict()
            )
            self.log.debug("Header Read")
            self.log.debug(self.header)

            # Test list
            self.tests: pd.DataFram = pd.read_excel(
                xls,
                sheet_name="Test_List",
                index_col=0,
                header=0,
                dtype=col_dtype,
            )
            self.log.debug("Test_List Read")
            self.log.debug(self.tests.head(5))

            # Data from each site. Store in dict with key as sheetname
            self.data: dict[str, pd.DataFrame] = {}  # empty dict
            for sheet_name in xls.sheet_names:
                if sheet_name not in [
                    "Header",
                    "Test_List",
                ]:  # reserved sheet names
                    try:
                        self.data[sheet_name] = pd.read_excel(
                            xls,
                            sheet_name=sheet_name,
                            index_col=[0, 1],
                            dtype=col_dtype,
                        )
                        self.log.debug(f"{sheet_name} loaded")
                        self.log.debug(self.data[sheet_name].head(5))
                    except Exception as e:
                        self.log.error(f"{sheet_name} failed to load\n{e}")

            self.log.info(f"{filepath} loaded with {len(self.data)} locations")
            self.log.debug(f"locations= {list(self.data.keys())}")

        except Exception as e:
            self.log.error(f"{filepath} failed to load\n{e}")

    def __repr__(self):
        """repr"""

        return (
            f"PN: {self.header['Part Number']}, locations ="
            f" {list(self.data.keys())}"
        )

    def xbar(
        self,
        location: Optional[Union[str, list[str]]] = None,
        test_id: Optional[str] = None,
        capability_loc: Optional[str] = None,
        **kwargs: bool,
    ):
        """Plot an xbar chart (value against SN) using SPCFigure module

        Args:
            location (Optional[Union[str, list[str]]], optional): Sheetname(s)
            test_id (Optional[str], optional): id of the test
                in test list to plot, default to plot all tests seperately
            capability_loc (Optional[str], optional): Sheetname for cp & cpk
                default is to not calculate for multiple locations
            meanline (bool, optional): Plot a meanline for each location
                off bv default
            violin (bool, optional): Plot a violin for each location
                off bv default
            to plot data for, default is to plot all locations

        """

        # List to hold all plots
        figs = []

        if test_id is None:
            self.log.debug("Plotting all tests")
            # Plot all tests
            for t_id in self.tests.index.get_level_values(0).unique():
                self.log.debug(f"Plotting {t_id}")
                figs.append(
                    self.xbar_plot(
                        t_id,
                        location=location,
                        capability_loc=capability_loc,
                        **kwargs,
                    )
                )

        else:
            # Plot one test
            self.log.debug(f"Plotting 1 test {test_id}")

            figs.append(
                self.xbar_plot(
                    t_id,
                    location=location,
                    capability_loc=capability_loc,
                    **kwargs,
                )
            )

        # Display all figures generated
        for fig in figs:
            fig.show()

    def xbar_plot(
        self,
        test_id: str,
        location: Optional[Union[str, list[str]]] = None,
        capability_loc: Optional[str] = None,
        **kwargs: bool,
    ):
        """Plot an xbar chart (value against SN),
         using SPCFigure module for a single tes

        Args:
            test_id (str): id of the test in test list to plot
            location (Optional[Union[str, list[str]]], optional): Sheetname(s)
            capability_loc (Optional[str], optional): sheetname for cp & cpk
                required if data is a dict else capability is ignored
                to plot data for, default is to plot all locations
            meanline (bool, optional): Plot a meanline for each location
                off bv default
            violin (bool, optional): Plot a violin for each location
                off bv default
            to plot data for, default is to plot all locations

        """

        # Check if capability is needed
        if (
            isinstance(location, list) or location is None
        ):  # Multiple locations
            if capability_loc is not None:

                self.log.debug(
                    f"Calculating capability for {capability_loc}, test"
                    f" {test_id}"
                )

                # Get Limits
                lsl, usl = self.get_limits(test_id)

                # Calcualte cp and cpk for specified location
                try:
                    cp, cpk = PartNumber.calculate_capability(
                        PartNumber.extract_test(
                            self.data[capability_loc], test_id
                        ),
                        lsl,
                        usl,
                    )
                except KeyError as e:
                    self.log.error(f"Invalid capability_loc -\n{e}")

            else:
                self.log.debug(
                    "Not calculating capability, capability_loc not set"
                )
                cp, cpk = np.nan, np.nan

        else:
            self.log.debug("Calculating capability for single location")

            # Get Limits

            lsl, usl = self.get_limits(test_id)

            cp, cpk = PartNumber.calculate_capability(
                PartNumber.extract_test(self.data, test_id), lsl, usl
            )

            # set capability_loc for the single location requested
            if capability_loc is None:
                capability_loc = location

        # Create figure to write too
        fig = SPCFigure(
            title=f"""{self.header['Part Number']}-{self.tests.loc[test_id]['Test_Name']},
                {capability_loc} Cp/Cpk={cp:.2f}/{cpk:.2f}"""
        )

        # extract test to plot

        # if location is none then it is all
        if location is None:
            location = list(self.data.keys())

        if isinstance(location, list):
            # multiple locations so extract single test for all
            datasets = {}
            for loc in location:
                datasets[loc] = PartNumber.extract_test(
                    self.data[loc], test_id
                )
        else:
            datasets = {}  # pass a 1 entry dict
            datasets[location] = PartNumber.extract_test(
                self.data[location], test_id
            )

        fig.xbar_plot(
            datasets,
            self.tests.loc[test_id],
            meanline=kwargs["meanline"],
            violin=kwargs["violin"],
        )
        return fig

    def get_limits(self, test_id: str) -> tuple[float, float]:
        """Get upper and lower spec limits

        Args:
            test_id (str): Test id in test list

        Returns:
            tuple[float, float]: USL, LSL
        """

        lsl = self.tests.loc[test_id]["Min_Tol"]
        usl = self.tests.loc[test_id]["Max_Tol"]
        # if not specified set to None
        if np.isnan(usl):
            usl = None
        if np.isnan(lsl):
            lsl = None

        return lsl, usl

    @staticmethod
    def calculate_capability(
        test_dataset: pd.DataFrame,
        usl: Union[int, float, None],
        lsl: Union[int, float, None],
    ) -> Tuple[float, float]:
        """Calculate capability for a dataset filtered to a single test and location

        Args:
            test_dataset (pd.DataFrame): Dataset reduced to a single test
            usl (Union[int, float, None]): Upper Spec Limit
            lsl (Union[int, float, None]): Lower Spec Limit

        """
        log = logging.getLogger(__name__)

        mean = statistics.mean(test_dataset["Reading"])
        SD = statistics.stdev(test_dataset["Reading"])

        # Error check
        if lsl is None and usl is None:
            log.error("Neither Min_Tol or Max_Tol is set")
            raise ValueError("Neither Min_Tol or Max_Tol is set")

        if usl is None:
            cpk = (mean - lsl) / (3 * SD)
            cp = np.nan
        elif lsl is None:
            cpk = (usl - mean) / (3 * SD)
            cp = np.nan
        else:
            cp = (usl - lsl) / (6 * SD)
            cpk = min((mean - lsl) / (3 * SD), (usl - mean) / (3 * SD))

        return cp, cpk

    @staticmethod
    def extract_test(dataset: pd.DataFrame, test_id: str) -> pd.DataFrame:
        """
        returns a dataset in the format needed by SPCFigure:
           * 1 location
           * 1 test
           * all SNs

        Args:
            dataset (pd.DataFrame): Single location to extract from
            test_id (str): test id in test list

        Returns:
            pd.DataFrame: Dataset reduced to a single test
        """
        return dataset.loc[test_id]