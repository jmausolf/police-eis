#!/usr/bin/python3
import pickle
import glob
from os import path
import dateutil.parser
from collections import namedtuple
import sys
from threading import Lock

from flask import abort

from webapp.evaluation import precision_at_x_proportion, compute_AUC, fpr_tpr
from webapp.evaluation import recall_at_x_proportion, compute_result_at_x_proportion
from webapp import config
import pdb

cache = {}
cache_lock = Lock()


def timestamp_from_path(pkl_path):
    prefix = path.join(config.results_folder, "police_eis_results_")
    ts = pkl_path.replace(prefix, "").split("_")[-1]
    ts = ts.replace(".pkl", "")
    print (ts)
    return ts


Experiment = namedtuple("Experiment", ["timestamp", "config", "score", "data",
                                       "fpr", "tpr", "fnr", "tnr", "recall", "precision", "aggregation",
                                       "eis_baseline", "threshold_levels"])


def experiment_summary(pkl_file):
    data = read_pickle(pkl_file)
    model_config = data["config"]
    if "parameters" not in model_config:
        model_config["parameters"] = "?"

    if "train_start_date" not in data:
        model_config["train_start_date"] = "01Jan1970"
    else:
        model_config["train_start_date"] = data["train_start_date"].strftime("%d%b%Y")

    model_config["test_end_date"] = data["test_end_date"].strftime("%d%b%Y")


    #model_config["features"] = data["features"]
    #model_config["feature_summary"] = feature_summary(model_config["officer_features"])
    model_config["feature_summary"] = feature_count(model_config["officer_features"])
    prec_at = precision_at_x_proportion(
        data["test_labels"], data["test_predictions"],
        x_proportion=0.01)
    auc_model = compute_AUC(data["test_labels"], data["test_predictions"])
    num_units = len(data["test_labels"])

    threshold_levels = [10.0, 15.0, 25.0]
    #fpr, tpr, fnr, tnr = {}, {}, {}, {}
    fpr, tpr, fnr, tnr = [], [], [], []

    for percent in sorted(list(threshold_levels)):
        #threshold_levels.append(each_threshold)
        #fpr.update({each_threshold: [0, 1]})
        #tpr.update({each_threshold: [1, 1]})
        #fnr.update({each_threshold: [1, 0]})
        #tnr.update({each_threshold: [0, 0]})
        eis_baseline = None

        # Raw counts of officers we are flagging correctly and incorrectly at various fractions of the test set.
        fpr.append(compute_result_at_x_proportion(data["test_labels"], data["test_predictions"], 'FP', x_proportion=percent/100.0))
        fnr.append(compute_result_at_x_proportion(data["test_labels"], data["test_predictions"], 'FN', x_proportion=percent/100.0))
        tpr.append(compute_result_at_x_proportion(data["test_labels"], data["test_predictions"], 'TP', x_proportion=percent/100.0))
        tnr.append(compute_result_at_x_proportion(data["test_labels"], data["test_predictions"], 'TN', x_proportion=percent/100.0))



    """
    for each_threshold in sorted(list(data["eis_baseline"].keys())):
        threshold_levels.append(each_threshold)
        fpr.update({each_threshold: data["eis_baseline"][each_threshold]["dsapp"][0, 1]})
        tpr.update({each_threshold: data["eis_baseline"][each_threshold]["dsapp"][1, 1]})
        fnr.update({each_threshold: data["eis_baseline"][each_threshold]["dsapp"][1, 0]})
        tnr.update({each_threshold: data["eis_baseline"][each_threshold]["dsapp"][0, 0]})
        eis_baseline = data["eis_baseline"][each_threshold]["eis"]
    """

    rec_list = []
    pre_list = []
    for percent in [10.0, 15.0, 25.0]:
        rec_list.append(recall_at_x_proportion(data["test_labels"],
            data["test_predictions"], x_proportion=percent/100.0))
        pre_list.append(precision_at_x_proportion(data["test_labels"],
            data["test_predictions"], x_proportion=percent/100.0))

    try:
        aggregation = data["aggregation"]
    except:
        aggregation = "No aggregated data stored"

    recall = "[{}, {}, {}]".format(rec_list[0].round(2), rec_list[1].round(2), rec_list[2].round(2))
    precision = "[{}, {}, {}]".format(pre_list[0].round(2), pre_list[1].round(2), pre_list[2].round(2))
    #return Experiment(dateutil.parser.parse(timestamp_from_path(pkl_file)),
    #                  model_config, auc_model, data, fpr, tpr, fnr, tnr,
    #                  recall, aggregation, eis_baseline, threshold_levels)

    return Experiment(dateutil.parser.parse(timestamp_from_path(pkl_file)),
                      model_config, auc_model, data, fpr, tpr, fnr, tnr,
                      recall, precision, aggregation, eis_baseline, threshold_levels)


def update_experiments_cache():
    experiments = glob.glob(config.results_folder)
    experiments = glob.glob(path.join(config.results_folder, "*.pkl"))
    with cache_lock:
        for pkl in experiments:
            ts = timestamp_from_path(pkl)
            if ts not in cache:
                cache[ts] = experiment_summary(pkl)
                #print("ts not in cache")
                pass
    # todo delete experiments that were remove from cache


def read_pickle(pkl_file):
    with open(pkl_file, "rb") as f:
        if sys.version_info < (3, 0):
            content = pickle.load(f)
        else:
            content = pickle.load(f, encoding='latin1')
    return content


def get_labels_predictions(timestamp):
    update_experiments_cache()
    # risk of dirty reads here because outside of lock
    if timestamp not in cache:
        abort(404)
    exp = cache[timestamp]
    return exp.data["test_labels"], exp.data["test_predictions"]


def get_aggregate_scores(timestamp):
    update_experiments_cache()
    # risk of dirty reads here because outside of lock
    if timestamp not in cache:
        abort(404)
    exp = cache[timestamp]
    return exp.aggregation


def get_baselines(timestamp):
    update_experiments_cache()
    # risk of dirty reads here because outside of lock
    if timestamp not in cache:
        abort(404)
    exp = cache[timestamp]
    return exp.eis_baseline, exp.fpr, exp.tpr, exp.fnr, exp.tnr, exp.threshold_levels, exp.config


def get_feature_importances(timestamp):
    update_experiments_cache()
    # risk of dirty reads here because outside of lock
    if timestamp not in cache:
        abort(404)
    exp = cache[timestamp]
    return exp.data["feature_importances_names"], exp.data["feature_importances"]


def get_experiments_list():
    update_experiments_cache()
    # risk of dirty reads here because outside of lock
    experiments_copy = [Experiment(e.timestamp, e.config,
                                   e.score, None, e.fpr,
                                   e.tpr, e.fnr, e.tnr, e.recall, e.precision, e.aggregation,
                                   e.eis_baseline, e.threshold_levels) for e in cache.values()]
    return experiments_copy


def feature_count(features):
    count = len(features)
    return count

def feature_summary(features):
    known_features = ['height_weight', 'education', 'daysexperience',
                      'yearsexperience', 'malefemale', 'race', 'officerage',
                      'officerageathire', 'maritalstatus', 'careerarrests',
                      'numrecentarrests', 'careerNPCarrests', '1yrNPCarrests',
                      'careerdiscarrests', '1yrdiscarrests', 'arresttod',
                      'arresteeage', 'disconlyarrests', 'arrestratedelta',
                      'arresttimeseries', 'arrestcentroids', 'careernpccitations',
                      '1yrnpccitations', 'careercitations', '1yrcitations',
                      'numsuicides', 'numjuveniles', 'numdomesticviolence',
                      'numhate', 'numnarcotics', 'numgang', 'numpersweaps',
                      'numgunknife', 'avgagevictims', 'minagevictims',
                      'careerficount', '1yrficount', 'careernontrafficficount',
                      '1yrnontrafficficount', 'careerhighcrimefi',
                      '1yrhighcrimefi', '1yrloiterfi', 'careerloiterfi',
                      'careerblackfi', 'careerwhitefi', 'avgsuspectagefi',
                      'avgtimeofdayfi', 'fitimeseries', 'careercadstats',
                      '1yrcadstats', '1yrcadterms', 'careercadterms',
                      'careerelectivetrain', '1yrelectivetrain',
                      'careerhourstrain', '1yrhourstrain', 'careerworkouthours',
                      '1yrworkouthours', 'careerrochours', '1yrrochours',
                      'careerproftrain', '1yrproftrain',
                      'careertrafficstopnum', '1yrtrafficstopnum',
                      'careerdomvioltrain',
                      '1yrdomvioltrain', 'careermilitarytrain', '1yrmilitarytrain',
                      'careertasertrain', '1yrtasertrain', 'careerbiastrain',
                      '1yrbiastrain', 'careerforcetrain', '1yrforcetrain',
                      'careertsuofarr', '1yrtsuofarr', 'careerforcetraffic',
                      '1yrforcetraffic', 'careertsblackdaynight',
                      '1yrtsblackdaynight', 'careertrafstopresist', '1yrtrafstopresist',
                      '3yrtrafstopresist', '5yrtrafstopresist',
                      '1yrtrafstopsearch', '3yrtrafstopsearch',
                      '5yrtrafstopsearch', 'careertrafstopsearch', '1yrtrafstopsearchreason',
                      '3yrtrafstopsearchreason', '5yrtrafstopsearchreason',
                      'careertrafstopsearchreason', '1yrtrafstopruntagreason',
                      '3yrtrafstopruntagreason', '5yrtrafstopruntagreason',
                      'careertrafstopruntagreason', '1yrtrafstopresult',
                      '3yrtrafstopresult', '5yrtrafstopresult', 'careertrafstopresult',
                      '1yrtrafstopbyrace', '3yrtrafstopbyrace', '5yrtrafstopbyrace',
                      'careertrafstopbyrace', '1yrtrafstopbygender',
                      '3yrtrafstopbygender', '5yrtrafstopbygender',
                      'careertrafstopbygender', 'trafficstoptimeseries', '1yreiswarnings',
                      '5yreiswarnings', 'careereiswarnings', '1yreiswarningtypes',
                      'careereiswarningtypes', '1yreiswarninginterventions',
                      'careereiswarninginterventions', '1yrextradutyhours', 'careerextradutyhours',
                      '1yrextradutyneighb1', 'careerextradutyneighb1', '1yrextradutyneighb2',
                      'careerextradutyneighb2', '1yrneighb1', 'careerneighb1',
                      '1yrneighb2', 'careerneighb2', '1yrprioralladverse', 'careerprioralladverse',
                      '1yrprioraccident', 'careerprioraccident', '1yrnumfilteredadverse',
                      'careernumfilteredadverse', '1yrroccoc', 'careerroccoc', '1yrrocia',
                      'careerrocia', '1yrpreventable', 'careerpreventable',
                      '1yrunjustified', 'careerunjustified', '1yrsustaincompl',
                      'careersustaincompl', '1yriaconcerns',
                      'careeriaconcerns', 'careeriarate',
                      '1yrdofcounts', 'careerdofcounts',
                      '1yrdirectivecounts',
                      'careerdirectivecounts', '1yriaeventtypes', 'careeriaeventtypes',
                      '1yrinterventions', 'careerinterventions',
                      '1yrweaponsuse', 'careerweaponsuse',
                      '1yrunithistory', 'careerunithistory', '1yrdivisionhistory',
                      'careerdivisionhistory']

    used_features = [key for key, val in features.items() if val == True]
    print(used_features)
    number_features = len(used_features)

    not_used = set(known_features) - set(used_features)
    if len(not_used) == 0:
        return "all"
    else:
        #pass
        not_used = [n for n in not_used if not n.startswith("imputation_")]
        # any_census_used = any([True for n in features
        #                       if n.startswith("rate_")])
        # if not any_census_used:
        #     not_used = [n for n in not_used if not n.startswith("rate_")]
        #     not_used.append("census")
        return "not used: {}".format(", ".join(not_used))

# will be run when webapp first starts
print("Initializing experiments list")
update_experiments_cache()
print("...finished")
