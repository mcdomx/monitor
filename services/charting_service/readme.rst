Charting Service
----------------

Overview
^^^^^^^^
This service is designed to act as a stand-alone service in a docker image.

This service will provide a chart for a monitor and will update that chart with new log data from that monitor, if it is running.

This service relies on the monitor application being up and running and serving requests so that the charting service can get data to plot.

Usage
^^^^^
To get the charting page example:
http://127.0.0.1:8100/monitor_chart?monitor_name=MyMonitor&start_date=2020-10-01&limit_start_days=10

This will return a full HTML page that displays a responsive chart which has the data for the monitor named 'MyMontior' with the data display starting on '2020-10-01' and will limit the number of days that the chart can be scrolled backwards by 10 days.  (Since monitors may have months or even years of data, this limit should be considered as a year's worth of chart data would take a while to retrieve.  Generally, 10 days is reasonable.)

The call returns an entire webpage that can be embedded into another web page or viewed as a separate webpage on its own.

To embed the the chart using HTML:

``<iframe class= "ml-1" id="plot-area" src="" width="100%" height="100%" style="border:none;"></iframe>``

...and set the src tag to the url.  You can do this with javascript:

``let target_div = document.getElementById('plot-area')
target_div.setAttribute('src', url)``


Docker Image
^^^^^^^^^^^^
To build and start the image:

``docker build --tag charting_service .``
``docker run -it -p 8200:8200 --rm charting_service``

or

``docker-compose up``

Once the image is running, the service will be available using the URL in the usage section of this document.