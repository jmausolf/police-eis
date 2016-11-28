import pandas as pd
from sqlalchemy import create_engine
import yaml
from webapp import app
import os

with open('../charlotte_pd.yaml') as f:
    config = yaml.load(f)

config = {
    'host':config['PGHOST'],
    'user':config['PGUSER'],
    'database':config['PGDATABASE'],
    'password':config['PGPASSWORD'],
    'port':config['PGPORT'],
}
dbengine = create_engine('postgres://', connect_args=config)


def get_best_models(timestamp, metric, parameter=None, number=25):

    """
    --------------------------------------------------------
    Get the REPORT of the best models
    by the specified timestamp and given metric

    RETURNS RUN TIME, MODEL TYPE, METRIC, and VALUE
    OR
    RUN TIME, MODEL TYPE, METRIC, PARAMETER, and VALUE
    --------------------------------------------------------
    ARGUMENTS:
        timestamp:  models run on or after given timestamp
                    example: '2016-08-03'
        metric:     metric to be optimized
                    example: 'precision@'
        parameter:  parameter value or threshold if any
                    default=None
                    example: '10.0'
        number:     maximum number of desired results
                    default = 25
    --------------------------------------------------------
    """
    if parameter is None:
        query = ("SELECT results.evaluations.model_id, run_time, model_type, metric, parameter, value FROM results.evaluations JOIN results.models "
                 "ON evaluations.model_id=models.model_id "
                 "WHERE run_time >= '{}' "
                 "AND value is not null "
                 "AND metric = '{}' "
                 "ORDER BY value DESC LIMIT {} ").format(timestamp, metric, number)

    elif parameter is not None:
        parameter = float(parameter)
        metric = metric + "@"
        query = ("SELECT results.evaluations.model_id, run_time, model_type, metric, parameter, value FROM results.evaluations JOIN results.models "
                 "ON evaluations.model_id=models.model_id "
                 "WHERE run_time >= '{}' "
                 "AND value is not null "
                 "AND metric = '{}' "
                 "AND parameter = '{}' "
                 "ORDER BY value DESC LIMIT {} ; ").format(timestamp, metric, parameter, number)

    df_models = pd.read_sql(query, con=dbengine)
    output = df_models
    return output


def get_model_prediction(id):
    query = ("SELECT unit_id, unit_score, label_value FROM results.predictions "
             "WHERE model_id = '{}' "
             "ORDER BY unit_score DESC ; ".format(id))

    df_models = pd.read_sql(query, con=dbengine)
    #print(df_models)
    output = df_models
    return output


def get_models(query_arg):

    #print("number: ", query_arg['number'])
    print("timestamp: ", query_arg['timestamp'])
    print("metric: ", query_arg['metric'])
    query_metric =''
    for q in range(len(query_arg['metric'])):
        query_metric += 'new_metric=$$'+query_arg['metric'][q]+'$$ or '

    query = ("BEGIN; "
             "SELECT public.colpivot(\'test\', \'SELECT * FROM "
             "(SELECT e.model_id, metric || parameter as new_metric, value "
             "FROM charlotte_pd.results.evaluations e join charlotte_pd.results.models m ON e.model_id=m.model_id "
             "where run_time >= $${}$$ ) t0 where new_metric NOTNULL and "
             "{}\', "
             "array['model_id'], array['new_metric'],'#.value',null); "
             "select * from test order by 2 desc; ").format(query_arg['timestamp'],query_metric[:-3])
    df_models = pd.read_sql(query, con=dbengine)
    output = df_models
    return output




