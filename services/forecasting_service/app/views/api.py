import logging

from django.shortcuts import render
from django.http import JsonResponse

from ..models.models import TrafficMonitorFeed, TrafficMonitorLogentry
from ..code.forecast import get_predictions
from ..code.train import train_and_save


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _parse_args(request, *args):
    """
    Helper function that will parse a series of URL arguments from a request.
    If an argument is not in the request, an exception is thrown.
    Arguments in the request that are not listed are not specified in the args
    argument are included in the returned dictionary even though they were not required.

    Usage:
        kwargs = _parse_args(request, 'required_arg1', 'required_arg2', ..)

    :param request: The HTTP request that should contain the arguments
    :param args: A list of string values that represent the names of arguments to parse
    :return: A dictionary where keys are the arguments and values the respective values of each argument in the request.
    """

    rv = {}

    for arg_name in args:
        arg_value = request.GET.get(arg_name)
        if not arg_value:
            raise Exception(f"'{arg_name}' parameter is required.")
        rv.update({arg_name: arg_value})

    other_args = set(request.GET.keys()).difference(rv.keys())
    for other_name in other_args:
        rv.update({other_name: request.GET.get(other_name)})

    return rv


def train(request):
    """ Train a model and save the configuration file.  Return config filename."""
    try:
        kwargs = _parse_args(request, 'monitor_name')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    if kwargs.get('interval') is None:
        kwargs.update({'interval': 60})
    else:
        kwargs.update({'interval': int(kwargs.get('interval'))})

    if kwargs.get('hours_in_training') is None:
        kwargs.update({'hours_in_training': 24})
    else:
        kwargs.update({'hours_in_training': int(kwargs.get('hours_in_training'))})

    if kwargs.get('hours_in_prediction') is None:
        kwargs.update({'hours_in_prediction': 24})
    else:
        kwargs.update({'hours_in_prediction': int(kwargs.get('hours_in_prediction'))})

    if kwargs.get('source_data_from_date') is None:
        kwargs.update({'source_data_from_date': '2020-01-01'})

    if kwargs.get('predictors') is None:
        kwargs.update({'string_predictor_columns': ['class_code', 'weekday', 'hour']})
    else:
        kwargs.update({'string_predictor_columns': [s.strip() for s in kwargs.get('predictors').split(',')]})
    del kwargs['predictors']

    print(f"KWARGS: {kwargs}")
    try:
        filename = train_and_save(**kwargs)
    except Exception as e:
        logger.error(e)
        logger.error(e.__traceback__)
        return JsonResponse({'error': e.args}, safe=False)

    return JsonResponse(filename, safe=False)


def predict(request):
    """ Load a trained model from a configuration file and return prediction
    based on the most recent observation data in the database. """

    try:
        kwargs = _parse_args(request, 'monitor_name')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    if kwargs.get('interval') is None:
        kwargs.update({'interval': 60})
    else:
        kwargs.update({'interval': int(kwargs.get('interval'))})

    if kwargs.get('hours_in_training') is None:
        kwargs.update({'hours_in_training': 24})
    else:
        kwargs.update({'hours_in_training': int(kwargs.get('hours_in_training'))})

    if kwargs.get('hours_in_prediction') is None:
        kwargs.update({'hours_in_prediction': 24})
    else:
        kwargs.update({'hours_in_prediction': int(kwargs.get('hours_in_prediction'))})

    return JsonResponse(get_predictions(**kwargs), safe=False)


def get_forecast(request):
    """
    Retrieve a forcast which is structured according to arguments provided:
    'monitor_name': name of monitor to predict
    'interval': default=60. number of minutes in each forecast interval
    'hours_in_prediction': default=24. number of hours to create predictions for
    'classes_to_predict': defaults to all available if no list of classes is provided.
    'from_date': defaults to first date available.  This is the date where training records are started.
        This option exists in the event that a large dataset is available and not all records are needed
        for training.
    :param request:
    :return:
    """

    try:
        kwargs = _parse_args(request, 'monitor_name')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    if kwargs.get('interval') is None:
        kwargs.update({'interval': 60})
    else:
        kwargs.update({'interval': int(kwargs.get('interval'))})

    if kwargs.get('hours_in_training') is None:
        kwargs.update({'hours_in_training': 24})
    else:
        kwargs.update({'hours_in_training': int(kwargs.get('hours_in_training'))})

    if kwargs.get('hours_in_prediction') is None:
        kwargs.update({'hours_in_prediction': 24})
    else:
        kwargs.update({'hours_in_prediction': int(kwargs.get('hours_in_prediction'))})

    if kwargs.get('source_data_from_date') is None:
        kwargs.update({'source_data_from_date': '2020-01-01'})

    try:
        fc_data = create_forecast(**kwargs)
    except Exception as e:
        logger.error(e)
        print(e.__traceback__)
        return JsonResponse({'error': e.args, 'trace': e.__traceback__}, safe=False)

    return JsonResponse(fc_data, safe=False)
