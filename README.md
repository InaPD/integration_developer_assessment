# Runnr.ai integration developer assessment
This repository contains working Django code. Run your code locally, you don't need any external services.
The repo also contains a sqlite database, it contains a single `Hotel` record that you can use for testing. The `pms_hotel_id` corresponds with the example payloads.

## Prerequisites:
- use Python version 3.11
- install dependencies by running: `pip install -r requirements.txt`

## Run server
`python manage.py runserver 0.0.0.0:8000`

## Relevant information
- The file `views.py` contains a webhook endpoint to receive updates from the PMS. These updates don't contain any details of the actual reservations. They require you to fetch additional details of any reservation.
- The file `external_api.py` mocks API calls that are available to you to get additional guest and reservation details. Note that the API calls sometimes generate errors, or invalid data. You should deal with those in the way you see fit.
- The file `pms_systems.py` contains an AbstractBaseClass and a ChildClass of a `PMS`. You will find explanations of what all the methods do inside the methods of the ABC.
- The file `models.py` contains your database models. The models should be mostly self-explanatory. Relations are defined and some columns have `help_text`.

## TODO
- Fork the repo into your own Github account. Make the fork public.
- Implement the child classes `PMS_Mews` in the file `pms_systems.py`: `clean_webhook_payload`, `handle_webhook`, `update_tomorrows_stays`, `stay_has_breakfast`.
- Webhook calls should use the `clean_webhook_payload`, `handle_webhook` methods. You should test the webhook functionality by making Postman POST request to the url: `http://localhost:8000/webhook/mews/` with the payload:
```
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
```
- imagine that the method `update_tomorrows_stays` runs every day in the evening to update the stays that will checkin tomorrow. You should test this by running a Django shell and calling the method manually. `python manage.py shell`
- The last method `stay_has_breakfast` can be called from anywhere in the code. It should return the correct value.


# Implementation

The implementation of the business logic for this assessment is done in the pms_systems.py file in the hotel app folder in the functions: `clean_webhook_payload`, `handle_webhook`, `update_tomorrows_stays`, `stay_has_breakfast`.

### clean_webhook_payload

The goal for this function was to clean up JSON payload that we receive from the request to the endpoint `webhook/str:pms_name>/`. The received JSON has a byte string payload and should be converted into a Unicode string using the UTF-8 encoding. After it is decoded it is converted into a python dictionary. Logic to remove possible duplicates in the 'Events' list is also implemented. This function returns a dictionary 


### handle_webhook

The handle_webhook function is used to process incoming changes of reservations from an external webhook that sends a request to the app. Each webhook can contain multiple reservation events. As the code iterates over the events, the following logic is performed:
- we retrieve information for the reservation and guest from an external API by ReservationId and GuestId. In the mock external API functions there is also a case when the API raises and exception as it it doesn't work. For this situation I impelemented a retry logic to try to execute the function multiple times.

- we update/create Guest using the phone number as identifier. If the external API doesn't retrieve a valid phone number, then the entry in the Stay table is created without a Guest object. The column language is populated by using the get_language(country) function, to map the country with corresponding language from the language_mapfile.py file. The default of the language is English, if no valid relation exists.

- we update/create Stay table with information on the reservation. The column status from this table is populated by mapping the reservation_statuses received from the external API to valid inputs for the Stay model through the reservation_mapfile.py. 

### update_tomorrows_stays

This function performs an automatic update of the reservations that are planned for the next day. The dataset of reservations are retrieved from the external API with the function `get_reservations_between_dates()`, filtered by check in date. After the data is retrieved it is formatted into a dictionary similar to the external input for the  `webhook/str:pms_name>/` endpoint and it is processed by the handle_webhhok function. This process is scheduled to be performed every day at 00:00. 

To test the logic of this function we can use the Django shell by executing `python manage.py shell ` in Terminal to open it. After it is opened we enter the following code block:
```
from hotel.pms_systems import PMS_Mews

pms_mews_instance = PMS_Mews()
pms_mews_instance.update_tomorrows_stays()

```

To schedule the execution of the update every day at 00:00 we use django apscheduler, which calls a function wiith similar logic to the django shell execution above. The function uses a CronTrigger object to schedule the update of stays for the following day. 

### stay_has_breakfast

This function checks if the reservation has breakfast included, by getting the reservation details from the external API filtered by the reservation id retrieved from the Stay object on input. 


For any additional questions you can contact me at ipopducheva@gmail.com

