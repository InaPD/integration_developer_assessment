from abc import ABC, abstractmethod
import inspect
import sys
import json
from datetime import datetime, timedelta
from typing import Optional
from django.shortcuts import get_object_or_404
from django.db import transaction
from language_mapfile import country_language_map
from reservation_mapfile import reservation_status_map

from hotel.external_api import (
    get_reservations_between_dates,
    get_reservation_details,
    get_guest_details,
    APIError,
)

from hotel.models import Stay, Guest, Hotel


class PMS(ABC):
    """
    Abstract class for Property Management Systems.
    """

    def __init__(self):
        pass

    @property
    def name(self):
        longname = self.__class__.__name__
        return longname[4:]

    @abstractmethod
    def clean_webhook_payload(self, payload: str) -> dict:
        """
        Clean the json payload and return a usable dict.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_webhook(self, webhook_data: dict) -> bool:
        """
        This method is called when we receive a webhook from the PMS.
        Handle webhook handles the events and updates relevant models in the database.
        Requirements:
            - Now that the PMS has notified you about an update of a reservation, you need to
                get more details of this reservation. For this, you can use the mock API
                call get_reservation_details(reservation_id).
            - Handle the payload for the correct hotel.
            - Update or create a Stay.
            - Update or create Guest details.
        """
        raise NotImplementedError

    @abstractmethod
    def update_tomorrows_stays(self) -> bool:
        """
        This method is called every day at 00:00 to update the stays checking in tomorrow.
        Requirements:
            - Get all stays checking in tomorrow by calling the mock API
                get_reservations_between_dates(checkin_date, checkout_date).
            - Update or create the Stays.
            - Update or create Guest details. Deal with missing and incomplete data yourself
                as you see fit. Deal with the Language yourself. country != language.
        """
        raise NotImplementedError

    @abstractmethod
    def stay_has_breakfast(self, stay: Stay) -> Optional[bool]:
        """
        This method is called when we want to know if the stay includes breakfast.
        Notice that the breakfast data is not stored in any of the models?
        How would you deal with this?
        Requirements:
            - Your input is a Stay object.
            - Return True if the stay includes breakfast, otherwise False. Return None if
                you don't know.
        """
        raise NotImplementedError


class PMS_Mews(PMS):
    def clean_webhook_payload(self, payload: str) -> dict:

        json_string = payload.decode('utf-8')
        data_dict = json.loads(json_string)
        #Remove duplicates
        data_dict["Events"] = list({event["Value"]["ReservationId"]: event for event in data_dict["Events"]}.values())
        return data_dict

    def handle_webhook(self, webhook_data: dict) -> bool:
        #self.update_tomorrows_stays()

        for event in webhook_data['Events']:

            print('====================== NEW RESERVATION ======================================')
            reservation_id=event["Value"]["ReservationId"]

            # # tuka moze i so retries 
            # try:
            #     details=json.loads(get_reservation_details(reservation_id))
            # except:
            #     # False tuka prekinuva se 
            #     return 
            
            details=json.loads(get_reservation_details(reservation_id))

                
            hotel_instance = get_object_or_404(Hotel, pms_hotel_id=details['HotelId'])

            guest_details=json.loads(get_guest_details(details['GuestId']))
            # print(guest_details)
            # print(type(guest_details))
            guest_phone=guest_details["Phone"]

            '''
            Since the guest name is not an identifier field, even if it not assigned we can create the 
            guest, only with an empty string fo the name
            '''
            if guest_details['Name'] is None:
                guest_details['Name']=''

            '''
            Since the phone is the main identifier a guest, and by extension fo the stay, if the
            phone number is invalid then we skip the creation or update of that guest.
            Ideally it would be better to return an error message to be able to identify the invalid entry, 
            but the handle webhook is designed here to return a boolean, so we just make the guest column None
            and not disrupt the execution of the function
            '''
            if guest_phone in ["Not available", "",None]:
                print('Continue')
                guest_instance=None
            else:
                # Try to get an existing Guest instance, if it exists update else create new guest entry
                guest_instance = Guest.objects.filter(phone=guest_phone).first()
                if guest_instance:
                    if guest_instance.name != guest_details["Name"]:
                        guest_instance.name = guest_details["Name"]

                    if guest_instance.language != get_language(guest_details["Country"]):
                        guest_instance.language = get_language(guest_details["Country"])

                    guest_instance.save()
                    
                else:
                    guest_instance=Guest.objects.create(
                    name=guest_details["Name"],
                    phone=guest_phone,
                    language=get_language(guest_details["Country"]))

            print(guest_instance)
            print('xxxxxxxxxxxxxxxxxx', hotel_instance,details['ReservationId'])

            # Try to get an existing Stay instance, if it exists update else create new stay entry
            stay_instance = Stay.objects.filter(hotel=hotel_instance, pms_reservation_id=details['ReservationId']).first()

            if stay_instance:
                print('Update')
                if stay_instance.hotel!= hotel_instance:
                    stay_instance.hotel=hotel_instance
                if stay_instance.guest!= guest_instance:
                    stay_instance.guest=guest_instance
                if stay_instance.pms_reservation_id!=details['ReservationId']:
                    stay_instance.pms_reservation_id=details['ReservationId']
                if stay_instance.pms_guest_id!=details['GuestId']:
                    stay_instance.pms_guest_id=details['GuestId']
                if stay_instance.status!=details['Status']:
                    stay_instance.status=reservation_status_map[details['Status']]
                if stay_instance.checkin!=details['CheckInDate']:
                    stay_instance.checkin=details['CheckInDate']
                if stay_instance.checkout!=details['CheckOutDate']:
                    stay_instance.checkout=details['CheckOutDate']
                
                stay_instance.save()

            else:
                print('stay else')
                stay_instance=Stay.objects.create(
                hotel=hotel_instance,
                guest=guest_instance,
                pms_reservation_id=details['ReservationId'],
                pms_guest_id=details["GuestId"],
                checkin= details['CheckInDate'],
                checkout=details['CheckOutDate'],
                status= reservation_status_map[details['Status']]
                )


        return True

    def update_tomorrows_stays(self) -> bool:

        tomorrow_date = datetime.now()+timedelta(days=1)
        tomorrow_date_string = tomorrow_date.strftime('%Y-%M-%D')
        reservations=json.loads(get_reservations_between_dates(tomorrow_date_string, ''))
        print(reservations)

        ret_reservations={}
        #Sort check in data in format as the test input
        for res in reservations:
            ret_reservations={}
            ret_reservations['HotelId']=res['HotelId']
            ret_reservations['IntegrationId']='Auto Update',
            ret_reservations['Events']=[{"Name":" ","Value":{"ReservationId":res["ReservationId"]}}]
            
            #Call handle_webhook function
            self.handle_webhook(ret_reservations)
            

        return True


    def stay_has_breakfast(self, stay: Stay) -> Optional[bool]:
        '''
        We call this function with a stay instance. Since the value of breakfast is not written in the Stay table,
        we have to get the reservation id and call the external_api function get_reservation_details() to get
        information on the breakfast 
        '''
        reservation_details=json.loads(get_reservation_details(stay.pms_reservation_id))
        return reservation_details["BreakfastIncluded"]
    

def get_pms(name):
    fullname = "PMS_" + name.capitalize()
    # find all class names in this module
    # from https://stackoverflow.com/questions/1796180/
    current_module = sys.modules[__name__]
    clsnames = [x[0] for x in inspect.getmembers(current_module, inspect.isclass)]

    # if we have a PMS class for the given name, return an instance of it
    return getattr(current_module, fullname)() if fullname in clsnames else False

def get_language(country):
    '''
    Function to get the language code from language_mapfile.py. It's always better to have 
    all country codes matched to language codes in one separate config file, so that changes
    can be made from one file. If the country code is not matched to any language, then
    the default language is English.
    '''
    if country in country_language_map.keys():
        print(country_language_map[country])
        return country_language_map[country]
    else:
        return country_language_map["GB"]