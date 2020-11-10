import logging
from pygam import LinearGAM

# from django.shortcuts import render
from django.http import JsonResponse

from ..code.model_inventory import ModelInventory, get_predictions


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
        filename = ModelInventory().create_model(**kwargs)
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

    preds = get_predictions(**kwargs)

    if preds is None:
        preds = {"success": False, "message": f"No models setup with args: {kwargs}"}

    return JsonResponse(preds, safe=False)


def get_available_models(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'monitor_name')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    return JsonResponse(ModelInventory().get_inventory_listing(kwargs.get('monitor_name')))


def get_model_by_filename(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'filename')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    return JsonResponse(ModelInventory().get_inventory_item(kwargs.get('filename')))


def retrain(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'filename')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    fname = ModelInventory().retrain_by_filename(kwargs.get('filename'))
    if fname is None:
        rv = {'success': False, 'message': f"No file with name '{kwargs.get('filename')}' exists."}
    else:
        rv = ModelInventory().get_inventory_item(fname)

    return JsonResponse({'success': True, 'message': rv}, safe=False)


def delete(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'filename')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)
    fname = ModelInventory().delete_model(kwargs.get('filename'))

    return JsonResponse(fname, safe=False)


def update_all(request) -> JsonResponse:
    try:
        kwargs = _parse_args(request, 'monitor_name')
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': e.args}, safe=False)

    return JsonResponse({'success': True, 'message': ModelInventory().retrain_all(**kwargs)}, safe=False)


