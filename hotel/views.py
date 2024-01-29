from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse

from hotel import pms_systems


@csrf_exempt
@require_POST
def webhook(request, pms_name):
    """
    Assume a webhook call from the PMS with a status update for a reservation.
    The webhook call is a POST request to the url: /webhook/<pms_name>/ Eg. /webhook/mews/
    The body of the request is a JSON string with the following format:
    {
        "HotelId": "851df8c8-90f2-4c4a-8e01-a4fc46b25178",
        "IntegrationId": "c8bee838-7fb1-4f4e-8fac-ac87008b2f90",
        "Events": [
            {
                "Name": "ReservationUpdated",
                "Value": {
                    "ReservationId": "5a9469b7-f13f-4a8d-b092-afe400fd7721"
                }
            },
            {
                "Name": "ReservationUpdated",
                "Value": {
                    "ReservationId": "7c22cb23-c517-48f9-a5d4-da811043bd67"
                }
            },
            {
                "Name": "ReservationUpdated",
                "Value": {
                    "ReservationId": "7c22cb23-c517-48f9-a5d4-da811023bd67"
                }
            }
        ]
    }
    """

    pms = pms_systems.get_pms(pms_name)

    payload_cleaned = pms.clean_webhook_payload(request.body)
    
    success = pms.handle_webhook(payload_cleaned)

    if not success:
       return HttpResponse(status=400)
    else: 
        return HttpResponse("Thanks for the update.")
    
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from apscheduler.triggers.cron import CronTrigger

from hotel.pms_systems import PMS_Mews

scheduler = BackgroundScheduler()



scheduler.add_jobstore(DjangoJobStore(), "default")


@register_job(
    scheduler,
    CronTrigger(hour=0, minute=0, second=0, timezone="Europe/Skopje"),
    replace_existing=True
)
def my_scheduled_task1():
    # Your task logic goes here
    pms_instance= PMS_Mews()
    pms_instance.update_tomorrows_stays()
    print("Task executed!")

register_events(scheduler)

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    # Allow graceful shutdown when needed
    scheduler.shutdown()