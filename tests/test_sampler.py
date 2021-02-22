# -*- coding: utf-8 -*-

import pytest

import evensampling
from io import StringIO
import pandas as pd

__author__ = "Your Name"
__copyright__ = "Your Name"
__license__ = "mit"


def test_fib():
    past_6_days_io = StringIO(
    """area,n
    London,25
    Birmingham,25
    Cardiff,25
    Kent,0
    """)
    past_6_days = pd.read_csv(past_6_days_io)


    case_numbers_io = StringIO(
    """area,cases
    London,25
    Birmingham,5
    Cardiff,25
    Kent,25
    """)
    case_numbers = pd.read_csv(case_numbers_io)

    box_manifest_io = StringIO(
    """box,plate,coord,area,priority
    boxC5,plate33B,A5,Cardiff,0
    boxC2,plate123A,A1,Cardiff,0
    box1,plate123A,A2,London,0
    box1,plate1413A,A3,London,0
    box1,plate15B,A4,Kent,0
    box2,plate26A,A1,London,0
    box2b,plate25B,A1,London,0
    box3,plate23C,A1,Kent,0
    box3,plate22D,A1,Birmingham,1
    """)
    box_manifest = pd.read_csv(box_manifest_io)
    options = {
            'seconds_per_cherrypick' : 10,
        'seconds_per_box_load' : 60*20,

        'total_time_available' : 60*20*1000000000 ,

        'area_loss_weighting' : 2,

        'maximise_samples_weighting' :1,

        'priority_sample_weighting' : 10,
            'max_samples':10,
            'max_boxes':2,
            'max_search_time':10 #in seconds
        }


    mysampler = evensampling.Sampler(previous_aggregated_results=past_6_days,
                                     true_case_numbers=case_numbers,
                                     options=options)
    mysampler.make_picks(box_manifest)
