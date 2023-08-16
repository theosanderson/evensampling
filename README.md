# Evensampling

Evensampling is a package that was developed at pace during the SARS-CoV-2 pandemic to select microplates for sequencing in the UK. The package models the process of picking samples from plates and allows constraints to be specified on the total time available for picking, the total number of plates and samples that can be picked, and on the maximum number of boxes that can be used. Subject to these constraints, and presented with information on how many samples from different areas have been picked during the preceding 6 days and data on case numbers in each area, the package optimizes the selection process based on user-defined parameters. At the peak of the sequencing response to the pandemic, it was used to pick up around 10,000 samples per day, and over the course of the pandemic picked millions of samples. 

A major goal of Evensampling is to ensure that genomes sampled in an area per week are proportional to case numbers, creating a  representative distribution of sequenced genomes, even if for logistical reasons input samples may not be representative. This alignment with the epidemiological situation enables the identification of trends and patterns. The algorithm inherently corrects for issues that have appeared in previous days. If, due to technical or logistical challenges, samples from a particular area don't arrive one day, the algorithm will prioritize more of them to be picked the next day to compensate. This adaptive nature helps to maintain a balanced and consistent approach over time.

The algorithm also considers a priority weight associated with each sample, allowing prioritised picking of sequences from travellers or other prioritised groups. The algorithm is implemented using OR-tools, minimising a composite loss function to balance various competing requirements and preferences.

## Installation


```bash
pip install git+https://github.com/theosanderson/evensampling.git
```

For a simple example see [this test](./tests/test_sampler.py)
