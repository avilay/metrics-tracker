# Metrics Tracker

This will be a website that can easily be viewed on a mobile phone as well as on a desktop. Its purpose is to help the user track a bunch of metrics - their value along with the timestamp when it was recorded - and then analyze the movement of these metrics over time. They should be able to analyze individual metrics as well overlay multiple metrics and look at their movement over time.

By default is should be possible to group all metrics by timeseries with a configurable aggregate function, e.g., it should be possible to view the weekly average of exercise minutes. Here "exercise" is the metric, "minutes" is the unit of measurement, "average" is the aggregator function, and "weekly" is the property that is being grouped.

Users should be able to track the following different types of metrics. I have provided a possible way to model the data, but it is not the only way, feel free to suggest other data models. All the data models have a `recorded_at` field whose values are timestamps.

## Binary Metrics

This is the simplest type of metric. An example is to track when they meditate. The "meditate" metric will just have a timestamp to record when they meditated. 

#### Data Model

| recorded_at |
| ----------- |
| 1767619980  |
| 1769852880  |
| 1770687180  |

#### Filtering

This metric cannot be filtered.

#### Grouping

Only the default timeseries grouping is possible. `count` is the only aggregate function that can be used. Here is what it would look like -

**Weekly Meditation Count**

| Week   | Count |
| ------ | ----- |
| week 1 | 3     |
| week 2 | 4     |

## Real Valued Metric

This is another simple metric where the value is a real number along with the unit of measurement. For example "weight" which is measured in "lbs". 

#### Data Model

| recorded_on | value |
| ----------- | ----- |
| 1767486480  | 180   |
| 1767996960  | 190   |
| 1770784620  | 183   |

#### Filtering

This metric cannot be filtered.

#### Grouping

Only default timeseries grouping is possbile. Various aggregate functions like `sum`, `average`, `median`, `standard_deviation`, etc. can be used. Here is what it can look like -

**Average Weekly Weight**

| Week   | Average |
| ------ | ------- |
| week 1 | 180.2   |
| week 2 | 192.4   |

## Categorical Metric

The metric can take one of a fixed number of string values, or categories. An example is to track users' mood, which can be happy, sad, serene, and angry.

#### Data Model

| recorded_at | value  |
| ----------- | ------ |
| 1767996960  | Happy  |
| 1769872140  | Happy  |
| 1770732360  | Serene |
| 1770784620  | Sad    |
| 1771975380  | Happy  |

#### Filtering

This metric cannot be filtered.

#### Grouping

Timeseries is the first level of grouping, within that they can be grouped by their values. Only `count` aggregate function can be used, e.g., 

**Weekly Mood Count**

| Week   | Value                      | Count           |
| ------ | -------------------------- | --------------- |
| week 1 | Happy<br />Sad<br />Serene | 2<br />3<br />4 |
| week 2 | Happy<br />Angry<br />Sad  | 3<br />1<br />2 |

## Metrics with Properties

These are metrics where each reading has a bunch of properties associated with them. There are two variants of this - firstly where each reading will have values for each property, lets call this type of metric as "cross-product properties", and secondly where a reading will have properties based the value of some other property, lets call this type of metric as "conditional properties". The metric can optionally have a real number as value, or it can just be the timestamp along with the property values.

### Cross-Product Properties

Each property can have one of several string values. The metric space of metric readings can be thought of as the cross-product of different values that each property can take. For example, user wants to track their food. The "food" metric has the following properties:

* Source: This property can take one of the values "home-cookied", "take-out", "tiffin".
* Taste: This property can take one of the values "delicious", "edible", "bad".
* Is_Filling: This property can take one of True or False.
* Healthy: This property can take values "very", "medium", "no".

#### Data Model

| recorded_on | source      | taste     | is_filling | healthy |
| ----------- | ----------- | --------- | ---------- | ------- |
| 1767486480  | home-cooked | delicious | True       | very    |
| 1767996960  | tiffin      | edible    | True       | medium  |
| 1769852880  | home-cooked | bad       | False      | very    |

#### Filtering

The metric can be filtered by any property/value, e.g., I can filter for all home cooked food that was tasty.

#### Grouping

The metric can be grouped by any property. Continuing the filtering example, I can group all home cooked food that was tasty by how healthy it was. Here is what it would look like -

**Weekly Count of source == "home-cooked" && taste == "delicious" Food grouped by Healthy** 

| Week   | Healthy                  | Count           |
| ------ | ------------------------ | --------------- |
| week 1 | very<br />medium<br />no | 3<br />4<br />1 |
| week 2 | very<br />medium<br />no | 5<br />2<br />0 |

#### Conditional Properties

This is best explained by an example. Lets say user wants to track their blood glucose. The "blood-glucose" metric can have a property "meal" which can take values "fasting", "breakfast", "lunch", "snack", "dinner". If the value of "meal" is any thing other than "fasting", a second property called "delta" can take on one of the values from like "one-hour-after", "two-hours-after", and "before". But the "delta" property doesn't make much sense if the "meal" is "fasting". The actual reading is a real number. Strictly speaking it is an integer, but we can keep it as a real number to make things simpler. The unit is "mg/dL".

#### Data Model

| recorded_on | meal      | delta           | value |
| ----------- | --------- | --------------- | ----- |
| 1767619980  | fasting   |                 | 101   |
| 1767996960  | breakfast | one-hour-after  | 150   |
| 1769852880  | breakfast | two-hours-after | 120   |

#### Filtering

The metric can be filtered by any property/value, e.g., I can filter for readings that I took one hour after any meal, so the filter is `delta == "one-hour-after"`.

#### Grouping

Can group by any property. Given the value is a real number, the aggregate function can be configured.  Grouping all breakfast meals by the delta will look like this -

**Weekly Average of meal == "breakfast" Blood-Glucose by Delta**

| Week   | Delta                                           | Average               |
| ------ | ----------------------------------------------- | --------------------- |
| week 1 | before<br />one-hour-after<br />two-hours-after | 120<br />150<br />130 |
| week 2 | before<br />one-hour-after<br />two-hours-after | 120<br />150<br />130 |

## Analysis

Indvidual metrics can be filtered and grouped in timeseries for first level of analysis. As a second level, a specific configuration of filtered and grouped metric can be overlayed on another specific configuration of filtered and grouped metric to see how both of them move. This can be done for any number of metrics. The report can be saved so the user does not have to configure and overlay every time.

## User Tasks

There are really 4 high-level user tasks:

1. User is able to get a summary of their list of metrics.
2. User is able to add a new metric.
3. User is able to add a log entry for an existing metric.
4. User is able to analyze metrics.

I really like the UI of Apple Health app. Here are some screen shots.

<img src="./summary.PNG" alt="summary" style="zoom:33%;" />

<img src="./analyze_single_metric.PNG" alt="analyze_single_metric" style="zoom:33%;" />

<img src="./log_entry.PNG" alt="log_entry" style="zoom:33%;" />

## Additonal Notes

Instead of having such a structured way of defining and entering metrics, maybe have the user describe using free text what they are recording, e.g., they can record "blood glucose one hour after breakfast" and a value, and the system automatically figures out the schema for later analysis.